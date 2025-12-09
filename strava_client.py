import json
import time

import httpx
from fastapi import HTTPException
import datetime as dt
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session

from strava_auth import get_user_tokens
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, logger
from cache import (
    get_cached_strava_activities,
    cache_strava_activities,
)


async def fetch_activities_for_user(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 50
) -> list[dict]:
    """
    Загрузить активности конкретного пользователя из Strava.
    Returns empty list if user not connected to Strava.
    """
    try:
        tokens = await get_user_tokens(user_id, db)
    except ValueError as e:
        # User not connected to Strava
        logger.warning("strava_not_connected", user_id=user_id, error=str(e))
        return []  # Return empty list instead of raising error
    except Exception as e:
        logger.error("strava_fetch_error", user_id=user_id, error=str(e))
        return []
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"page": page, "per_page": per_page}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error("strava_api_error", user_id=user_id, error=str(e))
        return []


async def fetch_activities_last_n_weeks_for_user(
    user_id: int,
    db: Session,
    weeks: int = 12,
    use_cache: bool = True
) -> list[dict]:
    """
    Загрузить активности за последние N недель для пользователя.
    Поддерживает кеширование для оптимизации производительности.
    Returns empty list if user not connected to Strava.
    """
    import datetime as dt
    
    # Check cache first
    if use_cache:
        cached = get_cached_strava_activities(user_id, weeks)
        if cached is not None:
            logger.info("strava_activities_from_cache", user_id=user_id, weeks=weeks, count=len(cached))
            return cached
    
    # Cache miss - fetch from Strava
    try:
        tokens = await get_user_tokens(user_id, db)
    except ValueError as e:
        # User not connected to Strava
        logger.warning("strava_not_connected", user_id=user_id, weeks=weeks, error=str(e))
        return []  # Return empty list instead of raising error
    except Exception as e:
        logger.error("strava_fetch_error", user_id=user_id, weeks=weeks, error=str(e))
        return []
    
    logger.info("strava_activities_fetch", user_id=user_id, weeks=weeks)
    after_timestamp = int((dt.datetime.now() - dt.timedelta(weeks=weeks)).timestamp())
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    all_activities = []
    page = 1
    
    try:
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
    except Exception as e:
        logger.error("strava_api_error", user_id=user_id, weeks=weeks, error=str(e))
        return []
    
    # Cache the results
    if use_cache and all_activities:
        cache_strava_activities(user_id, weeks, all_activities)
        logger.info("strava_activities_cached", user_id=user_id, weeks=weeks, count=len(all_activities))
    
    return all_activities

async def fetch_activity_by_id(
    activity_id: int,
    user_id: int,
    db: Session,
    include_all_efforts: bool = False
) -> dict:
    """
    Fetch a single Strava activity for a specific user.
    Returns None if user not connected to Strava.
    """
    try:
        tokens = await get_user_tokens(user_id, db)
    except ValueError as e:
        # User not connected to Strava
        logger.warning("strava_not_connected", user_id=user_id, activity_id=activity_id, error=str(e))
        return None
    except Exception as e:
        logger.error("strava_fetch_error", user_id=user_id, activity_id=activity_id, error=str(e))
        return None
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    params = {"include_all_efforts": str(include_all_efforts).lower()}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("strava_api_error", user_id=user_id, activity_id=activity_id, error=str(e))
        return None

async def refresh_access_token_if_needed(user_id: int, db: Session, tokens: dict) -> dict:
    """
    Проверяем срок действия access_token для конкретного пользователя.
    Если истёк — обновляем через refresh_token и сохраняем в БД.
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
    # сохраняем обновлённые токены в БД для пользователя
    from strava_auth import save_user_tokens
    await save_user_tokens(user_id, db, new_tokens)
    logger.info("strava_token_refreshed", user_id=user_id)
    return new_tokens


async def exchange_code_for_token(code: str) -> dict:
    """
    Обмениваем authorization code от Strava на токены.
    Токены должны быть сохранены в БД через save_strava_tokens() после вызова этой функции.
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
    logger.info("strava_token_exchanged", athlete_id=token_data.get("athlete", {}).get("id"))
    
    # NOTE: Tokens should be saved to DB via save_strava_tokens() after this call
    # We no longer save to file for security reasons

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


async def fetch_activities(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 50
) -> list[dict]:
    """
    Тянем список активностей для конкретного пользователя (как /strava/activities).
    Returns empty list if user not connected to Strava.
    """
    try:
        tokens = await get_user_tokens(user_id, db)
    except ValueError as e:
        # User not connected to Strava
        logger.warning("strava_not_connected", user_id=user_id, error=str(e))
        return []  # Return empty list instead of raising error
    except Exception as e:
        logger.error("strava_fetch_error", user_id=user_id, error=str(e))
        return []
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    params = {
        "page": page,
        "per_page": per_page,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            logger.error("strava_api_error", user_id=user_id, status_code=resp.status_code)
            return []
        
        activities_raw = resp.json()
        return [_normalize_activity(a) for a in activities_raw]
    except Exception as e:
        logger.error("strava_api_error", user_id=user_id, error=str(e))
        return []


async def fetch_recent_activities_for_coach(
    user_id: int,
    db: Session,
    limit: int = 80
) -> list[dict]:
    """
    Тянем последние limit тренировок для конкретного пользователя, чтобы отправить их в GPT-коучу.
    Returns empty list if user not connected to Strava.
    """
    try:
        tokens = await get_user_tokens(user_id, db)
    except ValueError as e:
        # User not connected to Strava
        logger.warning("strava_not_connected", user_id=user_id, error=str(e))
        return []  # Return empty list instead of raising error
    except Exception as e:
        logger.error("strava_fetch_error", user_id=user_id, error=str(e))
        return []
    
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    activities: list[dict] = []
    page = 1
    per_page = 50

    try:
        async with httpx.AsyncClient() as client:
            while len(activities) < limit:
                params = {"page": page, "per_page": per_page}
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.error("strava_api_error", user_id=user_id, status_code=resp.status_code)
                    break

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

        logger.info("fetch_recent_activities_for_coach", user_id=user_id, count=len(activities))
        return activities
    except Exception as e:
        logger.error("strava_api_error", user_id=user_id, error=str(e))
        return []  # Return empty list instead of raising error

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def fetch_activities_last_n_weeks(
    user_id: int,
    db: Session,
    weeks: int = 8,
    use_cache: bool = True
) -> list[dict]:
    """
    Тянем активности за последние N недель для конкретного пользователя (по дате начала).
    Автоматически повторяет запрос до 3 раз при ошибках сети.
    """
    # Use the user-specific function
    return await fetch_activities_last_n_weeks_for_user(user_id, db, weeks, use_cache)

async def fetch_activities_between(
    user_id: int,
    db: Session,
    start_date: dt.date,
    end_date: dt.date
) -> list[dict]:
    """
    Тянем активности в диапазоне [start_date, end_date] для конкретного пользователя по start_date.
    Используем тот же формат словаря, что и в остальных функциях.
    """
    tokens = await get_user_tokens(user_id, db)
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

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
