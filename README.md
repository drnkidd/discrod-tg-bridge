# Discord–Telegram Bridge

Мост между Discord-сервером и Telegram: уведомления из каналов, пинги ролей, тикеты и полная модерация прямо из Telegram.

## Быстрый старт

### 1. Скопируй `.env.example` в `.env`
```bash
cp .env.example .env
```

### 2. Заполни `.env` (см. раздел ниже)

### 3. Запусти
```bash
docker compose up -d
```

### 4. Проверь логи
```bash
docker compose logs -f app
```

---

## Что нужно заполнить в `.env`

| Переменная | Где взять |
|---|---|
| `DISCORD_TOKEN` | [Discord Developer Portal](https://discord.com/developers/applications) → Bot → Token |
| `DISCORD_GUILD_ID` | ПКМ на сервере → "Копировать ID" (нужен режим разработчика) |
| `DISCORD_MONITORED_CHANNELS` | ПКМ на канале → "Копировать ID", несколько через запятую |
| `DISCORD_MONITORED_CATEGORIES` | ПКМ на категории → "Копировать ID" |
| `DISCORD_TICKETS_CHANNEL_ID` | ПКМ на канале тикетов → "Копировать ID" |
| `DISCORD_WATCHED_ROLE_IDS` | Настройки сервера → Роли → ПКМ → "Копировать ID" |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → /newbot |
| `TELEGRAM_NOTIFICATIONS_CHAT_ID` | Добавь бота в канал, отправь сообщение, [getUpdates](https://api.telegram.org/bot<TOKEN>/getUpdates) |
| `TELEGRAM_PINGS_CHAT_ID` | Аналогично |
| `TELEGRAM_TICKETS_CHAT_ID` | Группа с кнопками модерации |
| `TELEGRAM_OWNER_ID` | [@userinfobot](https://t.me/userinfobot) |

---

## Права Discord-бота

На Discord Developer Portal включи следующие **Bot Permissions**:
- `Manage Messages`
- `Kick Members`
- `Ban Members`
- `Moderate Members` (Timeout)
- `Read Messages / View Channels`
- `Send Messages`

**Privileged Intents:**
- `Server Members Intent` ✅
- `Message Content Intent` ✅

---

## Команды Telegram-бота

| Команда | Описание |
|---|---|
| `/ban <id>` | Забанить пользователя Discord |
| `/unban <id>` | Разбанить пользователя |
| `/mute <id>` | Замьютить (Discord Timeout) |
| `/unmute <id>` | Размьютить |
| `/warn <id>` | Выдать предупреждение |
| `/history <id>` | История нарушений |
| `/admins` | Список администраторов |
| `/addadmin <tg_id>` | Добавить администратора |
| `/removeadmin <tg_id>` | Удалить администратора |

---

## Управление

```bash
# 1. Перейти в каталог проекта
cd "C:\Users\Maxim\OneDrive\Desktop\discrod-telegram"

# 2. Поднять БД и Redis
docker-compose up -d postgres redis

# 3. Проверить доступные сервисы
docker-compose config --services
# Должно вывести: postgres, redis, app, migrate

# 4. Запустить миграции
docker-compose run --rm migrate

# 5. Запустить приложение
docker-compose up -d app
docker-compose logs -f app
```
