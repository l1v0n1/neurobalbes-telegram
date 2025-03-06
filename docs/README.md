# Neurobalbes Telegram Bot

Telegram бот нейробалбес, который общается в чатах на основе ваших сообщений.

## Возможности

- Создание демотиваторов с пользовательским текстом
- Создание цитат на изображениях
- Поддержка VIP-статуса для расширенного функционала
- Автоматическое масштабирование текста под размер изображения
- Поддержка водяных знаков

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/l1v0n1/neurobalbes-telegram.git
cd neurobalbes-telegram
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или
.venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r app/requirements.txt
```

4. Отредактируйте файл конфигурации `config.py` своими данными в директории app/core/:
```
# Bot settings
API_TOKEN = '123:123-123'
admin = 123
channel = 'https://t.me/123'
channel_name = '@123'
add_to_chat_link = 'http://t.me/123?startgroup=start'
chat = 'https://t.me/123_chat'
bot_username = '@123_bot'

# Donate settings
donate = 'https://www.donationalerts.com/r/spasibo_za_donati'
donatetoken = '123'

# Payment settings
premiumamount = 149
payoksecret = '123'
payokapi = '123-123-123'
payokapiid = '123'
payokshopid= 3222

# Version and github url
version = '2.0.1'
github_url = 'https://github.com/l1v0n1/neurobalbes-telegram'
```

## Запуск

```bash
python -m app.run
```

## Структура проекта

```
app/
├── api/          # API интеграции
├── core/         # Ядро бота
├── database/     # Работа с базой данных
├── media/        # Медиа ресурсы
│   ├── fonts/    # Шрифты
│   └── temp/     # Временные файлы
├── utils/        # Вспомогательные функции
└── requirements.txt
```

## Лицензия

MIT License
