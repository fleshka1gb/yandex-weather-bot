# 🎯 Yandex Weather Sniper (Ижевск) 24/7 на GitHub Actions

Автономный бот для автоматического подтверждения погоды и выставления зонтиков на Яндекс.Картах (г. Ижевск). Работает в облаке GitHub Actions **круглосуточно и бесплатно** без необходимости держать включённым свой компьютер.

---

## 📋 Как запустить бота за 5 шагов

### Шаг 1. Создайте репозиторий на GitHub
1. Зайдите на [github.com/new](https://github.com/new).
2. В поле **Repository name** укажите: `yandex-weather-bot`.
3. Выберите **Public** *(в публичных репозиториях GitHub Actions абсолютно бесплатен и безлимитен)*.
4. Нажмите **Create repository**.

---

### Шаг 2. Загрузите файлы в репозиторий
Вы можете загрузить файлы через Git или прямо через веб-интерфейс GitHub:

**Способ через Git (в папке проекта):**
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/yandex-weather-bot.git
git push -u origin main
```

**Или через веб-интерфейс:**
На странице вашего репозитория нажмите кнопку **Add file** -> **Upload files**, перетащите все файлы из папки `yandex_weather_bot` и нажмите **Commit changes**.

---

### Шаг 3. Создайте Telegram-бота (для уведомлений на телефон)
1. В Telegram найдите бота **[@BotFather](https://t.me/BotFather)** и отправьте команду `/newbot`.
2. Введите имя бота (например: `Izhevsk Weather Sniper`) и юзернейм (например: `izhevsk_weather_sniper_bot`).
3. Скопируйте полученный **HTTP API Token** (например: `7123456789:AAFn...`).
4. Нажмите **Start** в вашем новом созданном боте, чтобы он мог присылать вам сообщения.
5. Чтобы узнать свой Chat ID, напишите боту **[@userinfobot](https://t.me/userinfobot)** — он пришлёт ваш числовой `Id` (например: `123456789`).

---

### Шаг 4. Добавьте секреты в репозиторий GitHub
1. В вашем репозитории на GitHub перейдите в **Settings** (Настройки).
2. В левом меню выберите **Secrets and variables** $\rightarrow$ **Actions**.
3. Нажмите кнопку **New repository secret** и добавьте два секрета:
   - Имя: `TELEGRAM_BOT_TOKEN` | Значение: *токен от BotFather*
   - Имя: `TELEGRAM_CHAT_ID` | Значение: *ваш числовой ID из @userinfobot*

---

### Шаг 5. Включите права на запись статистики
1. В **Settings** репозитория перейдите в **Actions** $\rightarrow$ **General**.
2. Прокрутите вниз до раздела **Workflow permissions**.
3. Выберите **Read and write permissions** (чтобы бот мог сохранять `stats.json` со статистикой).
4. Нажмите **Save**.

---

## 🚀 Проверка и запуск

1. Перейдите во вкладку **Actions** в вашем репозитории на GitHub.
2. В левой колонке нажмите на **Yandex Weather Sniper (Izhevsk)**.
3. Нажмите кнопку **Run workflow** $\rightarrow$ **Run workflow** (зелёная кнопка).
4. Через 20–30 секунд бот завершит работу, и вам в Telegram придёт отчёт со статистикой за сегодня!

Теперь бот будет автоматически запускаться **каждые 15 минут круглосуточно 24/7**!
