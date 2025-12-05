import json
import time
from typing import List

import httpx
from fastapi import HTTPException
import datetime as dt
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session

from strava_auth import get_user_tokens
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, TOKENS_FILE, logger
from state_store import load_state, save_state

STRAVA_TOKENS_STATE_KEY = "strava_tokens"


async def fetch_activities_for_user(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 50
) -> list[dict]:
    """
    Загрузить активности конкретного пользователя из Strava.
    """
    tokens = await get_user_tokens(user_id, db)
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params={"page": page, "per_page": per_page}
        )
        response.raise_for_status()
        return response.json()


async def fetch_activities_last_n_weeks_for_user(
    user_id: int,
    db: Session,
    weeks: int = 12
) -> list[dict]:
    """
    Загрузить активности за последние N недель для пользователя.
    """
    import datetime as dt
    
    after_timestamp = int((dt.datetime.now() - dt.timedelta(weeks=weeks)).timestamp())
    
    tokens = await get_user_tokens(user_id, db)
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    all_activities = []
    page = 1
    
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                url,
                headers=headers,
                params={"after": after_timestamp, "page": page, "per_page": 100}
            )
            response.raise_for_status()
            activities = response.json()
            
            if not activities:
                break
            
            all_activities.extend(activities)
            page += 1
            
            # Safety limit
            if page > 10:
                break
    
    return all_activities

async def fetch_activity_by_id(
    activity_id: int,
    user_id: int,
    db: Session,
    include_all_efforts: bool = False
) -> dict:
    """
    Fetch a single Strava activity for a specific user.
    """
    tokens = await get_user_tokens(user_id, db)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    params = {"include_all_efforts": str(include_all_efforts).lower()}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)

    resp.raise_for_status()
    return resp.json()

def _write_tokens_file(token_data: dict) -> None:
    try:
        TOKENS_FILE.write_text(
            json.dumps(token_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to persist Strava tokens to disk: %s", e)


def _persist_tokens(token_data: dict) -> None:
    _write_tokens_file(token_data)
    try:
        save_state(STRAVA_TOKENS_STATE_KEY, token_data)
    except Exception as e:
        logger.warning("Failed to persist Strava tokens to DB: %s", e)


def load_tokens() -> dict:
    """
    Загружаем токены из файла strava_token.json.
    Если файла нет, пробуем восстановить их из БД.
    """
    if not TOKENS_FILE.exists():
        try:
            persisted = load_state(STRAVA_TOKENS_STATE_KEY)
        except Exception as e:
            logger.warning("Failed to load Strava tokens from DB: %s", e)
            persisted = None
        if not persisted:
            raise RuntimeError("No Strava tokens found. Authorize first via /auth/strava/login")
        _write_tokens_file(persisted)
        return persisted
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


async def refresh_access_token_if_needed(tokens: dict) -> dict:
    """
    Проверяем срок действия access_token.
    Если истёк — обновляем через refresh_token.
    Strava кладёт expires_at как UNIX timestamp в секундах.
    """
    expires_at = tokens.get("expires_at")

    # небольшой запас 60 секунд
    if expires_at and expires_at > time.time() + 60:
        return tokens  # токен ещё жив

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No refresh_token available to refresh access_token")

    token_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)

    if resp.status_code != 200:
        raise RuntimeError(f"Error refreshing Strava token: {resp.text}")

    new_tokens = resp.json()
    # сохраняем обновлённые токены в файл
    _persist_tokens(new_tokens)
    return new_tokens


async def get_valid_access_token() -> str:
    """
    Возвращает актуальный access_token:
    - читает из файла
    - при необходимости обновляет
    """
    tokens = load_tokens()
    tokens = await refresh_access_token_if_needed(tokens)
    return tokens["access_token"]


async def exchange_code_for_token(code: str) -> dict:
    """
    Обмениваем authorization code от Strava на токены и сохраняем их в файл.
    """
    token_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Error from Strava token endpoint: {resp.text}",
        )

    token_data = resp.json()

    # Сохраняем токены в файл в UTF-8
    _persist_tokens(token_data)

    return token_data


def _normalize_activity(a: dict) -> dict:
    """
    Приводим raw-активность Strava к единому формату, который дальше
    ожидают все модули (analytics, training_zones, predictions, progress и т.д.).

    Ключевые поля:
    - distance: метры
    - moving_time: секунды
    - elapsed_time: секунды
    Дополнительно оставляем синонимы distance_m / moving_time_s для обратной совместимости.
    """
    distance = a.get("distance")
    moving_time = a.get("moving_time")
    elapsed_time = a.get("elapsed_time")

    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "sport_type": a.get("sport_type") or a.get("type"),
        "start_date": a.get("start_date"),
        # унифицированные имена
        "distance": distance,
        "moving_time": moving_time,
        "elapsed_time": elapsed_time,
        # синонимы для старого кода
        "distance_m": distance,
        "moving_time_s": moving_time,
        "elapsed_time_s": elapsed_time,
        "total_elevation_gain_m": a.get("total_elevation_gain"),
        "average_speed_m_s": a.get("average_speed"),
        "has_heartrate": a.get("has_heartrate"),
        "average_heartrate": a.get("average_heartrate"),
        "max_heartrate": a.get("max_heartrate"),
        "kudos_count": a.get("kudos_count"),
    }


async def fetch_activities(page: int = 1, per_page: int = 50) -> list[dict]:
    """
    Тянем список активностей (как /strava/activities).
    """
    access_token = await get_valid_access_token()

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "page": page,
        "per_page": per_page,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    activities_raw = resp.json()

    return [_normalize_activity(a) for a in activities_raw]


async def fetch_recent_activities_for_coach(limit: int = 80) -> list[dict]:
    """
    Тянем последние limit тренировок, чтобы отправить их в GPT-коучу.
    """
    try:
        access_token = await get_valid_access_token()
        url = "https://www.strava.com/api/v3/athlete/activities"
        headers = {"Authorization": f"Bearer {access_token}"}

        activities: list[dict] = []
        page = 1
        per_page = 50

        async with httpx.AsyncClient() as client:
            while len(activities) < limit:
                params = {"page": page, "per_page": per_page}
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)

                chunk = resp.json()
                if not chunk:
                    break

                for a in chunk:
                    activities.append(_normalize_activity(a))
                    if len(activities) >= limit:
                        break

                if len(chunk) < per_page:
                    break  # больше страниц нет
                page += 1

        return activities
    except httpx.HTTPError as e:
        logger.error("strava_network_error", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to Strava. Please try again later."
        )
    except Exception as e:
        logger.error("unexpected_error_fetching_activities", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching activities."
        )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def fetch_activities_last_n_weeks(weeks: int = 8) -> list[dict]:
    """
    Тянем активности за последние N недель (по дате начала).
    Автоматически повторяет запрос до 3 раз при ошибках сети.
    """
    access_token = await get_valid_access_token()
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(weeks=weeks)

    activities: list[dict] = []
    page = 1
    per_page = 50
    reached_cutoff = False

    async with httpx.AsyncClient() as client:
        while not reached_cutoff:
            params = {"page": page, "per_page": per_page}
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                logger.warning(
                    "strava_api_error",
                    status_code=resp.status_code,
                    page=page,
                    detail=resp.text[:100],
                )
                if resp.status_code == 429:
                    logger.error("strava_rate_limit_hit")
                raise httpx.HTTPError(f"Strava API error: {resp.status_code} {resp.text}")

            chunk = resp.json()
            if not chunk:
                break

            for a in chunk:
                raw_start = a.get("start_date")
                dt_start = None
                if raw_start:
                    try:
                        # Строка типа "2025-03-10T18:12:34Z"
                        dt_start = dt.datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
                    except ValueError:
                        dt_start = None

                if dt_start and dt_start < cutoff:
                    reached_cutoff = True
                    break

                activities.append(_normalize_activity(a))

            if reached_cutoff:
                break

            if len(chunk) < per_page:
                break  # дальше активностей нет

            page += 1

    return activities

async def fetch_activities_between(start_date: dt.date, end_date: dt.date) -> list[dict]:
    """
    Тянем активности в диапазоне [start_date, end_date] по start_date.
    Используем тот же формат словаря, что и в остальных функциях.
    """
    access_token = await get_valid_access_token()
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    activities: list[dict] = []
    page = 1
    per_page = 50
    done = False

    async with httpx.AsyncClient() as client:
        while not done:
            params = {"page": page, "per_page": per_page}
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            chunk = resp.json()
            if not chunk:
                break

            for a in chunk:
                raw_start = a.get("start_date")
                if not raw_start:
                    continue
                try:
                    dt_start = dt.datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
                except ValueError:
                    continue

                d = dt_start.date()

                # Страве всё равно на наш диапазон — сами фильтруем
                if d < start_date:
                    # дальше только старее, можно останавливать цикл
                    done = True
                    break
                if d > end_date:
                    # слишком свежие, просто пропускаем
                    continue

                activities.append(_normalize_activity(a))

            if done:
                break
            if len(chunk) < per_page:
                break

            page += 1

    return activities
