# Быстрый тест изоляции пользователей

## Шаг 1: Запустите backend

В отдельном терминале:

```bash
# Активируйте виртуальное окружение
.\venv\Scripts\Activate.ps1

# Запустите backend
python -m uvicorn main:app --reload --port 8000
```

Дождитесь сообщения:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Шаг 2: Запустите тест

В другом терминале:

```bash
# Активируйте виртуальное окружение (если нужно)
.\venv\Scripts\Activate.ps1

# Запустите тест
python test_user_isolation.py
```

## Альтернатива: Используйте PowerShell скрипт

```powershell
.\run_test.ps1
```

## Что проверяет тест:

1. ✅ Регистрация User A (user_a@test.com)
2. ✅ Создание цели "Ironman 2025" для User A
3. ✅ Проверка, что User A видит свою цель
4. ✅ Выход User A
5. ✅ Регистрация User B (user_b@test.com)
6. ✅ Проверка, что дашборд User B ПУСТ (нет данных User A)
7. ✅ Создание цели "Marathon sub 4" для User B
8. ✅ Проверка, что User B видит только свою цель
9. ✅ Выход User B
10. ✅ Вход User A
11. ✅ Проверка, что User A видит только "Ironman 2025" (НЕ "Marathon sub 4")

## Ожидаемый результат:

```
✅ ALL TESTS PASSED - User isolation works correctly!
```

## Если backend на другом URL:

```bash
python test_user_isolation.py http://your-backend-url.com
```

## Устранение проблем:

### Backend не запускается:
- Проверьте, что все зависимости установлены: `pip install -r requirements.txt`
- Проверьте переменные окружения в `.env`
- Проверьте, что порт 8000 свободен

### Тест не может подключиться:
- Убедитесь, что backend запущен и доступен
- Проверьте URL в скрипте (по умолчанию `http://localhost:8000`)
- Проверьте firewall/антивирус

### Ошибки базы данных:
- Убедитесь, что база данных настроена
- Проверьте `DATABASE_URL` в `.env`
- При необходимости очистите базу: `DELETE FROM users CASCADE;`

