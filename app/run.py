#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для запуска Telegram-бота Нейробалбес
"""

import os
import sys

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем и запускаем основной модуль
from app.main import main

if __name__ == "__main__":
    main()
