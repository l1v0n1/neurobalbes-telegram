"""
Главный файл приложения, точка входа для запуска бота
"""

import logging
import os
import sys

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.bot import dp, bot, on_startup, on_shutdown
from aiogram import executor

def main():
	"""
	Основная функция для запуска бота
	"""
	# Настройка логирования
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler("bot.log"),
			logging.StreamHandler()
		]
	)
	
	# Запуск бота
	executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)

if __name__ == "__main__":
	main() 