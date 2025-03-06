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

4. Создайте файл конфигурации `.env` в корневой директории:
```env
BOT_TOKEN=your_telegram_bot_token
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
