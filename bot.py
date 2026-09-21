import os
import json
import re
import random
from datetime import datetime, timezone, timedelta
import requests
from playwright.sync_api import sync_playwright

# --- КОНФИГУРАЦИЯ ---
CITY_NAME = "Ижевск"
CITY_SLUG = "izhevsk"
WEATHER_URL = f"https://yandex.ru/pogoda/{CITY_SLUG}"
MAP_URL = f"https://yandex.ru/pogoda/{CITY_SLUG}/maps/nowcast"

# Координаты г. Ижевск
LATITUDE = 56.8498
LONGITUDE = 53.2045

# Часовой пояс Ижевска (UTC+4 / Самара)
IZHEVSK_TZ = timezone(timedelta(hours=4))

# Telegram секреты из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")


def get_current_izhevsk_time():
    """Возвращает текущее время в Ижевске (UTC+4)."""
    return datetime.now(IZHEVSK_TZ)


def get_schedule_mode(now_dt):
    """
    Определяет режим работы на основе дня недели и времени суток в Ижевске:
    1. Ночь (23:00 - 09:00): Сон / пропуск проверки.
    2. Рабочий день (Пн-Пт 09:00 - 18:00): Интервал 15-20 мин.
    3. Вечер будней (Пн-Пт 18:00 - 23:00): Интервал 15-60 мин (в среднем ~35 мин).
    4. Выходные (Сб-Вс 09:00 - 23:00): Интервал 15-60 мин (в среднем ~35 мин).
    """
    weekday = now_dt.weekday()  # 0 = Пн, 4 = Пт, 5 = Сб, 6 = Вс
    hour = now_dt.hour
    is_weekend = weekday >= 5

    # 1. Ночной режим отдыха
    if hour >= 23 or hour < 9:
        return {
            "mode": "night",
            "name": "💤 Ночной отдых (23:00 - 09:00)",
            "should_run": False,
            "min_interval_minutes": 60
        }

    # 2. Будни: рабочий день (09:00 - 18:00)
    if not is_weekend and (9 <= hour < 18):
        # 15-20 минут
        target_delay = random.randint(15, 20)
        return {
            "mode": "workday_rush",
            "name": "🏢 Рабочий день (09:00 - 18:00)",
            "should_run": True,
            "min_interval_minutes": target_delay
        }

    # 3. Будни: вечер (18:00 - 23:00)
    if not is_weekend and (18 <= hour < 23):
        target_delay = random.randint(30, 50)
        return {
            "mode": "workday_evening",
            "name": "🌆 Вечер будней (18:00 - 23:00)",
            "should_run": True,
            "min_interval_minutes": target_delay
        }

    # 4. Выходные: дневное/вечернее время (09:00 - 23:00)
    if is_weekend and (9 <= hour < 23):
        target_delay = random.randint(30, 50)
        return {
            "mode": "weekend",
            "name": "🏖 Выходной день (09:00 - 23:00)",
            "should_run": True,
            "min_interval_minutes": target_delay
        }

    return {
        "mode": "default",
        "name": "Стандартный режим",
        "should_run": True,
        "min_interval_minutes": 20
    }


def send_telegram_notification(message: str):
    """Отправляет форматированное сообщение в Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Токен или Chat ID не заданы. Пропуск отправки.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[Telegram] Уведомление успешно отправлено!")
        else:
            print(f"[Telegram] Ошибка отправки: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[Telegram] Исключение при отправке: {e}")


def load_stats():
    """Загружает stats.json с авто-сбросом при смене дня."""
    now = get_current_izhevsk_time()
    today_str = now.strftime("%Y-%m-%d")

    stats = {
        "date": today_str,
        "yes": 0,
        "no": 0,
        "total": 0,
        "last_run": "",
        "last_run_epoch": 0,
        "last_status": ""
    }

    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("date") == today_str:
                    stats = saved
                else:
                    # Переносим last_run_epoch для корректного расчета интервала
                    stats["last_run_epoch"] = saved.get("last_run_epoch", 0)
        except Exception as e:
            print(f"[Stats] Не удалось прочитать stats.json ({e}).")

    return stats


def save_stats(stats: dict):
    """Сохраняет stats.json."""
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Stats] Ошибка сохранения stats.json: {e}")


def detect_weather_condition():
    """Запрашивает HTML страницы погоды Ижевска и определяет, есть ли осадки."""
    print(f"[Parser] Проверка погоды для {CITY_NAME}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    is_raining = False
    status_text = "ясно"

    try:
        resp = requests.get(WEATHER_URL, headers=headers, timeout=15)
        html = resp.text

        now_match = re.search(r'Сейчас в\s*Ижевске\s*([^,\.]+)', html, re.IGNORECASE)
        meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)

        if now_match:
            status_text = now_match.group(1).strip()
        elif meta_match:
            status_text = meta_match.group(1).strip()

        full_check_text = (status_text + " " + html[:150000]).lower()
        rain_keywords = ["дождь", "ливень", "гроза", "морось", "ливневый", "дожд"]

        for kw in rain_keywords:
            idx = full_check_text.find(kw)
            if idx != -1:
                snippet = full_check_text[max(0, idx - 30): min(len(full_check_text), idx + 30)]
                if "без осадков" in snippet or "осадков не ожидается" in snippet or "нет осадков" in snippet:
                    continue
                is_raining = True
                break

        print(f"[Parser] Итог: Статус = «{status_text}», Дождь = {is_raining}")
    except Exception as e:
        print(f"[Parser] Ошибка парсинга погоды: {e}")

    return is_raining, status_text


def run_sniper_browser(is_raining: bool):
    """Запускает Headless Playwright, открывает карту и нажимает нужную кнопку."""
    target_text = "Да" if is_raining else "Нет"
    target_regex = r'^(да|да,\s*ид[её]т|ид[её]т|yes)\b' if is_raining else r'^(нет|нет,\s*не\s*ид[её]т|не\s*ид[её]т|без\s*осадков|no)\b'

    print(f"[Playwright] Запуск браузера. Целевая кнопка: «{target_text}»...")

    click_success = False
    clicked_label = ""
    error_message = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Samara",
            geolocation={"latitude": LATITUDE, "longitude": LONGITUDE},
            permissions=["geolocation"]
        )

        page = context.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(document, 'visibilityState', { get: () => 'visible', configurable: true });
            Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
        """)

        try:
            print(f"[Playwright] Переход на {MAP_URL}...")
            page.goto(MAP_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)

            found_button = None
            for attempt in range(25):
                elements = page.query_selector_all('button, [role="button"], a, div[class*="button"], div[class*="Button"], div[class*="feedback"]')

                for el in elements:
                    try:
                        text = (el.inner_text() or "").strip()
                        aria = (el.get_attribute("aria-label") or el.get_attribute("title") or "").strip()
                        clean_text = text.replace('\u00a0', ' ').strip()

                        if (clean_text.lower() == target_text.lower() or
                            re.search(target_regex, clean_text, re.IGNORECASE) or
                            re.search(target_regex, aria, re.IGNORECASE)):
                            found_button = el
                            clicked_label = clean_text or aria or target_text
                            break
                    except Exception:
                        continue

                if found_button:
                    print(f"[Playwright] Кнопка найдена: «{clicked_label}» на попытке {attempt + 1}")
                    break

                if attempt in (3, 8):
                    triggers = page.query_selector_all('button, [role="button"], [class*="feedback"], [class*="nowcast"]')
                    for trg in triggers:
                        try:
                            t_text = (trg.inner_text() or "").strip()
                            t_aria = (trg.get_attribute("aria-label") or "").strip()
                            if re.search(r'(сообщить.*осадк|сообщить.*погод|у вас ид[её]т дождь|ид[её]т ли дождь|осадки)', t_text + " " + t_aria, re.IGNORECASE):
                                print("[Playwright] Нажимаем кнопку вызова опросника...")
                                trg.click()
                                page.wait_for_timeout(1500)
                                break
                        except Exception:
                            continue

                page.wait_for_timeout(1000)

            if found_button:
                found_button.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                found_button.click(delay=100)
                page.wait_for_timeout(2000)
                click_success = True
                print(f"[Playwright] Успешно нажато: «{clicked_label}»")
            else:
                error_message = "Кнопка опроса («Да»/«Нет») не появилась на карте."
                print(f"[Playwright] {error_message}")

            page.screenshot(path="last_action.png")

        except Exception as e:
            error_message = f"Ошибка Playwright: {str(e)}"
            print(f"[Playwright] {error_message}")
        finally:
            context.close()
            browser.close()

    return click_success, clicked_label, error_message


def main():
    now_dt = get_current_izhevsk_time()
    now_epoch = int(now_dt.timestamp())
    now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')

    print("=" * 60)
    print(f"🚀 Yandex Weather Sniper (Ижевск) | {now_str}")
    
    # 1. Проверяем режим расписания
    schedule = get_schedule_mode(now_dt)
    print(f"⏰ Режим: {schedule['name']}")

    # Если ночной режим — выходим без лишней траты ресурсов
    if not schedule["should_run"]:
        print("💤 Ночное время: проверка пропущена (отдыхаем до утра 09:00).")
        print("=" * 60)
        return

    # 2. Проверяем, прошло ли достаточно времени с прошлого запуска
    stats = load_stats()
    last_run_epoch = stats.get("last_run_epoch", 0)
    elapsed_minutes = (now_epoch - last_run_epoch) / 60.0 if last_run_epoch > 0 else 999

    min_interval = schedule["min_interval_minutes"]
    if elapsed_minutes < min_interval:
        print(f"⏳ С момента прошлого клика прошло {elapsed_minutes:.1f} мин. (Интервал режима: {min_interval} мин.) Пропуск запуска.")
        print("=" * 60)
        return

    # 3. Определяем погоду
    is_raining, status_desc = detect_weather_condition()
    action_type = "yes" if is_raining else "no"

    # 4. Запускаем браузер и кликаем
    success, clicked_label, error_msg = run_sniper_browser(is_raining)

    # 5. Обновляем статистику
    today_str = now_dt.strftime("%Y-%m-%d")
    stats["date"] = today_str
    stats["last_run"] = now_str
    stats["last_run_epoch"] = now_epoch
    stats["last_status"] = status_desc

    if success:
        if action_type == "yes":
            stats["yes"] = stats.get("yes", 0) + 1
        else:
            stats["no"] = stats.get("no", 0) + 1
        stats["total"] = stats.get("yes", 0) + stats.get("no", 0)
        save_stats(stats)

        action_name = "«Да» (Зонтик отправлен ☔)" if action_type == "yes" else "«Нет» (Осадков нет ☀️)"

        msg = (
            f"🎯 <b>Яндекс.Метео Снайпер (Ижевск)</b>\n\n"
            f"✅ <b>Действие:</b> Нажал {action_name}\n"
            f"🌤 <b>Погода:</b> {status_desc}\n"
            f"⏰ <b>Режим:</b> {schedule['name']}\n\n"
            f"📊 <b>Статистика за сегодня ({stats['date']}):</b>\n"
            f"• ☔ <b>Да (дождь):</b> {stats['yes']}\n"
            f"• ☀️ <b>Нет (ясно):</b> {stats['no']}\n"
            f"• 📈 <b>Всего нажатий:</b> {stats['total']}\n\n"
            f"🕒 <i>Время (Ижевск): {now_dt.strftime('%H:%M:%S')}</i>"
        )
    else:
        save_stats(stats)
        msg = (
            f"⚠️ <b>Яндекс.Метео Снайпер (Ижевск)</b>\n\n"
            f"❌ <b>Не удалось нажать:</b> {error_msg}\n"
            f"🌤 <b>Погода:</b> {status_desc}\n"
            f"⏰ <b>Режим:</b> {schedule['name']}\n\n"
            f"📊 <b>Статистика за сегодня:</b> Всего: {stats['total']} (Да: {stats['yes']} | Нет: {stats['no']})\n"
            f"🕒 <i>Время (Ижевск): {now_dt.strftime('%H:%M:%S')}</i>"
        )

    send_telegram_notification(msg)
    print("=" * 60)
    print(f"🏁 Завершено: {get_current_izhevsk_time().strftime('%H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
