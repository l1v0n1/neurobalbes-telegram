# -*- coding: utf-8 -*-
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from app.core.config import API_TOKEN, admin, donatetoken
from app.utils import keyboard
from app.database import database as db


logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN, timeout=200)
dp = Dispatcher(bot, storage=storage)


class adm(StatesGroup):
	send_text = State()


@dp.message_handler(commands="admin", chat_type=types.ChatType.PRIVATE)
async def admin_panel(message: types.Message):
	if int(message.chat.id) == admin:
		await message.answer("Админ-панель", reply_markup=keyboard.apanel)


@dp.callback_query_handler(lambda call: call.data.startswith("admin"))
async def adminpanel(call):
	if "rass" in call.data:
		await call.message.answer(
			"Введите текст для рассылки.\n\nДля отмены нажмите кнопку ниже 👇",
			reply_markup=keyboard.back,
		)
		await adm.send_text.set()
	elif "stats" in call.data:
		count = db.sender()
		await call.answer("Всего чатов: {}".format(len(count)))


@dp.message_handler(state=adm.send_text)
async def process_name(message: types.Message, state: FSMContext):
	if message.text == "Отмена":
		await message.answer(
			"Отмена! Возвращаю в главное меню.",
			reply_markup=types.ReplyKeyboardRemove(),
		)
		await state.finish()
	else:
		info = db.sender()
		await message.answer("Начинаю рассылку...")
		for i in range(len(info)):
			try:
				await state.finish()
				id = info[i][0].split('peer')[1]
				await bot.send_message(f'-{id}', str(message.text))
			except Exception as e:
				print(e)
		await message.answer("Рассылка завершена.", reply_markup=keyboard.help)



executor.start_polling(dp, skip_updates=True)