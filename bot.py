# -*- coding: utf-8 -*-
import logging
import random
import os
import time
import mc
from mc.builtin import validators
from mc.builtin.formatters import usual_syntax
import asyncio
from translatepy import Translator
from PIL import Image, ImageDraw, ImageFont
from porfir import porfirevich
from gtts import gTTS
from demotivators import Demotivator, Quote
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils import exceptions
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import requests
import aioschedule
from help_utils import images_to_grid
from dalle import dalle_api
from aiopayok import Payok

import config
from config import API_TOKEN, admin
import keyboard
import database as db


logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN, timeout=200)
dp = Dispatcher(bot, storage=storage)


payok = Payok(
	config.payokapiid, config.payokapi, config.payoksecret, config.payokshopid
)


dialogs = {}



translator = Translator()


class adm(StatesGroup):
	send_text = State()


class stick(StatesGroup):
	blocked = State()


def simbols_exists(word):
	s = """/@:"""
	return any(x for x in s if x in word)


@dp.message_handler(content_types=["new_chat_members"])
async def chat_invited(message: types.Message):
	hello_message = "дорова я нейробалбес\nкаждые 20 сообщений я генерирую мемы, так же могу генерить текст и голосовые сообщения, запоминаю ваши сообщения и картинки, которые вы отправляете\n\nне забудьте дать мне админку, а то я не смогу работать(\n\n/help - команды бота\n\n"
	for user in message.new_chat_members:
		if user.id == bot.id:
			user_channel_status = await bot.get_chat_member(
				chat_id="@neurobalbes", user_id=message.from_user.id
			)
			if user_channel_status["status"] != "left":
				await bot.send_message(
					message.chat.id, hello_message, reply_markup=keyboard.help
				)
			else:
				await bot.send_message(
					message.chat.id,
					"Вы не подписаны на канал бота, я выхожу.\nДобавьте меня когда подпишитесь",
					reply_markup=keyboard.help,
				)
				await bot.leave_chat(message.chat.id)


@dp.message_handler(commands="premium", chat_type=["group", "supergroup"])
async def premium(message: types.Message):
	with open("premium.txt", "r", encoding="utf8") as f:
		prem = f.read().splitlines()
	if str(message.chat.id) in prem:
		await message.answer("Это и так премиум чат")
	else:
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(
			types.InlineKeyboardButton("Приобрести", callback_data="buy_premium")
		)
		await message.answer(
			f"Премиум подписка для этого чата\nЦена: {config.premiumamount}₽\n\nВозможности:\nx2 лимиты (больше сохраняемых данных в 2 раза, сообщения, фотки, стикеры)",
			reply_markup=keyboard,
		)


@dp.callback_query_handler(text="buy_premium")
async def buy_premium(call: types.CallbackQuery):
	number = random.randint(1, 9999999999999)
	history = await payok.get_transactions()
	payments = [i.payment_id for i in history]
	if number not in payments:
		id = number
	else:
		id = random.randint(number + 1, 9999999999999)
	payment = await `payok`.create_pay(
		config.premiumamount,
		id,
		desc="Премиум подписка",
		success_url="https://t.me/neurobalbesbot",
	)
	keyboard = types.InlineKeyboardMarkup(row_width=1)
	keyboard.add(
		types.InlineKeyboardButton("Оплатить", payment),
		types.InlineKeyboardButton("Проверить оплату", callback_data=f"check_{id}"),
		types.InlineKeyboardButton("Отмена", callback_data="cancel_prem"),
	)
	await call.message.answer(
		'Приобретение премиум подписки\nИспользуйте кнопку "Оплатить", чтобы перейти к форме оплаты, после оплаты нажмите на кнопку "Проверить оплату"',
		reply_markup=keyboard,
	)


@dp.callback_query_handler(lambda call: call.data.startswith("check_"))
async def check_payment(call: types.CallbackQuery):
	data = call.data.split("_")[1]
	try:
		transaction = await payok.get_transactions(data)
		status = transaction.transaction_status
		if int(status) == 1:
			with open("premium.txt", "r", encoding="utf8") as file:
				prem = file.read().splitlines()
			if str(call.message.chat.id) not in prem:
				with open("premium.txt", "a+", encoding="utf8") as f:
					f.write(str(call.message.chat.id) + "\n")
				await call.message.edit_text(call.message.text)
				await call.answer(
					"Вы успешно приобрели премиум подписку для данного чата", True
				)
			else:
				await call.message.edit_text(call.message.text)
				await call.answer("Чат уже премиум", True)
		else:
			await call.answer("Не оплачено", True)
	except Exception as e:
		await call.answer("Не оплачено", True)


@dp.callback_query_handler(text="cancel_prem")
async def cancelpre(call: types.CallbackQuery):
	await call.message.edit_text("Покупка отменена")


@dp.message_handler(commands="admin", chat_type=types.ChatType.PRIVATE)
async def admin_panel(message: types.Message):
	if int(message.chat.id) == admin:
		await message.answer("Админ-панель", reply_markup=keyboard.apanel)


@dp.message_handler(commands="givevip", chat_type=types.ChatType.PRIVATE)
async def givevip(message: types.Message):
	if int(message.chat.id) == admin:
		args = message.get_args()
		with open("premium.txt", "a+", encoding="utf8") as f:
			f.write(str(args) + "\n")
		await message.answer(f"Vip выдано {args}")


@dp.message_handler(commands="backup", chat_type=types.ChatType.PRIVATE)
async def adimkap(message: types.Message):
	if int(message.chat.id) == admin:
		args = message.get_args()
		asyncio.create_task(scheduler(message.chat.id, args))
		await message.answer(f"Бэкап успешно активирован\nРаз в {args} часа")


async def send_backup(chat_id):
	upload = anon.upload("data.db", progressbar=False)
	two = anon.upload("premium.txt", progressbar=False)
	await bot.send_message(
		chat_id,
		f"Бекап бд телеграм!\n{upload.url.geturl()}\n\nБекап премиум телеграм\n{two.url.geturl()}",
	)


async def scheduler(chat_id, tm):
	aioschedule.every(int(tm)).hours.do(send_backup, chat_id)
	while True:
		await aioschedule.run_pending()
		await asyncio.sleep(1)


@dp.message_handler(content_types=["text"], chat_type=types.ChatType.PRIVATE)
async def private_handler(message: types.Message):
	print(message.text, message.chat.id)
	await message.answer("я работаю только в группах", reply_markup=keyboard.help)


@dp.message_handler(commands="help", chat_type=["group", "supergroup"])
async def help_message(message: types.Message):
	await message.answer("F.A.Q", reply_markup=keyboard.help)


@dp.message_handler(commands="info", chat_type=["group", "supergroup"])
async def info(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		base = db.fullbase(message.chat.id)
		cantalk = base["talk"]
		textleft = base["textleft"]
		text_lines = len(base["textbase"])
		pic_count = len(base["photobase"])
		stic_count = len(base["stickers"])
		blocks = len(base["blockedstickers"])
		if cantalk == 0:
			mode = (
				"Сейчас бот молчит\nЧтобы он начал писать, нажмите на кнопку silent.off"
			)
			kb = keyboard.silentoff
		else:
			mode = "До следующей генерации мема: {} сообщений".format(20 - textleft)
			kb = ""
		with open("premium.txt", "r", encoding="utf8") as premiums:
			prem = premiums.read().splitlines()
		if str(message.chat.id) in prem:
			vip = "⭐️Premium Chat"
			maxlen = 2000
			maxphoto = 1000
			maxstickers = 400
		else:
			vip = "Вы можете приобрести ⭐️Premium для этого чата, введя /premium"
			maxlen = 1000
			maxphoto = 500
			maxstickers = 200
		msg = "{}\nID чата: {}\nсохранено строк {}/{}\nсохранено фото {}/{}\nсохранено стикеров {}/{}\nзаблокированных стикеров: {}\n\n{}\n\n@neurobalbes_generation".format(
			vip,
			message.chat.id,
			text_lines,
			maxlen,
			pic_count,
			maxphoto,
			stic_count,
			maxstickers,
			blocks,
			mode,
		)
		if kb == "":
			await message.answer(msg)
		else:
			await message.answer(msg, reply_markup=kb)


@dp.message_handler(commands="settings", chat_type=["group", "supergroup"])
async def settings(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		can_talk, intelligent, speed = (
			database["talk"],
			database["intelligent"],
			database["speed"],
		)
		if can_talk == 1 and intelligent == 0:
			mode = "может отправлять сообщения"
		elif can_talk == 0:
			mode = "не может отправлять сообщения"
		elif intelligent == 1 and can_talk == 1:
			mode = "в грамотном режиме"
		await message.answer(
			"Настройки бота\n\nНа данный момент бот {}\nСкорость генерации бота: {}\n\nУкажите настройку:\nsilent.on - бот не может писать\nsilent.off - бот может писать\n\nintelligent.on - грамотный режим общения\nintelligent.off - обычный режим общения\n\nspeed - скорость генерации текста (чем больше число, тем медленнее генерация)\n\nИспользуйте клавиатуру ниже".format(
				mode, speed
			),
			reply_markup=keyboard.bset,
		)


@dp.message_handler(commands="gen", chat_type=["group", "supergroup"])
async def generate_text(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(texts)
		if text_lines >= 1:
			generator = mc.PhraseGenerator(samples=texts)
			random_text = await generator.generate_phrase(
				validators=[validators.words_count(minimal=1)]
			)
			await message.answer(random_text)


@dp.message_handler(commands="genanek", chat_type=["group", "supergroup"])
async def gen_anek(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		a1 = ["Штирлиц шел по лесу, вдруг ему за пазуху упала гусеница.\n«{}», подумал Штирлиц."]
		a2 = ["Шел медведь по лесу\nСел в машину и — {}"]
		a3 = ["Ебутся два клоуна, а один другому говорит: — «{}»"]
		a4 = ["Заходит как-то улитка в бар\nА Бармен ей отвечает\nМы улиток не обслуживаем\nИ выпинывает ее за дверь\nЧерез неделю поиходит улитка\nИ говорит: «{}»"]
		a5 = ["— Извините, а у вас огоньку не найдется?\n— «{}» - ответил медведь из машины"]
		anek = random.choice([a1,a2,a3,a4,a5])
		generator = mc.PhraseGenerator(samples=texts)
		random_text = await generator.generate_phrase(
			validators=[validators.words_count(minimal=1)]
		)
		await message.answer(anek[0].format(random_text))


@dp.message_handler(commands="gendialogue", chat_type=["group", "supergroup"])
async def generate_dlg(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(texts)
		if text_lines >= 4:
			parts = []
			for _ in range(random.randint(3, 4)):
				generator = mc.PhraseGenerator(samples=texts)
				random_text = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1)]
				)
				parts.append(random_text)
			response = "\n— ".join(parts)
			await message.answer(response)


@dp.message_handler(commands="gensyntax", chat_type=["group", "supergroup"])
async def generate_usual_syntax(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(texts)
		if text_lines >= 1:
			generator = mc.PhraseGenerator(samples=texts)
			random_text = await generator.generate_phrase(
				validators=[validators.words_count(minimal=1)],
				formatters=[usual_syntax],
			)
			await message.answer(random_text)


@dp.message_handler(commands="genvoice", chat_type=["group", "supergroup"])
async def generate_voice_message(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(texts)
		if text_lines >= 1:
			generator = mc.PhraseGenerator(samples=texts)
			random_text = await generator.generate_phrase(
				validators=[validators.words_count(minimal=1)]
			)
			random_file = (
				f"random_voice_{random.randint(0, 10000000000000000000000000)}.mp3"
			)
			try:
				tts = gTTS(text=random_text, lang="ru")
				tts.save(random_file)
				with open(random_file, "rb") as voice:
					await bot.send_voice(message.chat.id, voice)
					os.remove(random_file)
			except:
				os.remove(random_file)


@dp.message_handler(commands="gensymbols", chat_type=["group", "supergroup"])
async def generate_text_by_symbols(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(database["textbase"])
		count = message.get_args()
		if count.isdigit():
			count = int(count)
			if count <= 50 and count >= 1:
				if text_lines >= 50:
					try:
						generator = mc.PhraseGenerator(samples=texts)
						random_text = await generator.generate_phrase(
							validators=[
								validators.chars_count(minimal=count, maximal=count)
							]
						)
						await message.answer(random_text)
					except:
						await message.answer("Недостаточно сообщений для генерации.")
				else:
					await message.answer("Недостаточно сообщений для генерации.")
			else:
				await message.answer("Введите число от 1 до 50")
		else:
			await message.answer("Вы не ввели число")


@dp.message_handler(commands="genlong", chat_type=["group", "supergroup"])
async def generate_long_sentence(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(database["textbase"])
		if text_lines >= 100:
			try:
				generator = mc.PhraseGenerator(samples=texts)
				random_text = await generator.generate_phrase(
					validators=[validators.chars_count(minimal=50)]
				)
				await message.answer(random_text)
			except:
				await message.answer("Недостаточно сообщений для генерации.")
		else:
			await message.answer("Недостаточно сообщений для генерации.")


@dp.message_handler(commands="genpoem", chat_type=["group", "supergroup"])
async def generate_poem(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(database["textbase"])
		if text_lines >= 100:
			generator = mc.PhraseGenerator(samples=texts)
			poem = []
			poem.append("от знаменитого писателя - Нейробалбеса\n")
			for i in range(random.randint(4, 16)):
				phrase = await generator.generate_phrase(
					validators=[validators.words_count(minimal=4)],
					formatters=[usual_syntax],
				)
				poem.append(phrase)
			finish = "\n".join(poem)
			await message.answer(finish)
		else:
			await message.answer("Недостаточно сообщений для генерации")


@dp.message_handler(commands="genpoll", chat_type=["group", "supergroup"])
async def generate_poll(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(database["textbase"])
		if text_lines >= 4:
			generator = mc.PhraseGenerator(samples=texts)
			random_text = await generator.generate_phrase(
				validators=[validators.chars_count(minimal=1, maximal=100)]
			)
			random_text2 = await generator.generate_phrase(
				validators=[validators.chars_count(minimal=1, maximal=100)]
			)
			random_text3 = await generator.generate_phrase(
				validators=[validators.chars_count(minimal=1, maximal=100)]
			)
			random_text4 = await generator.generate_phrase(
				validators=[validators.chars_count(minimal=1, maximal=100)]
			)
			await bot.send_poll(
				message.chat.id, random_text, [random_text2, random_text3, random_text4]
			)


@dp.message_handler(commands="genbugurt", chat_type=["group", "supergroup"])
async def generate_bugurt(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		text_lines = len(texts)
		if text_lines >= 1:
			generator = mc.PhraseGenerator(samples=texts)
			bugurt = []
			for i in range(random.randint(2, 8)):
				phrase = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1)]
				)
				bugurt.append(phrase)
			finish = "\n@\n".join(bugurt)
			await message.answer(finish.upper())


@dp.message_handler(commands="cont", chat_type=["group", "supergroup"])
async def continue_sentence(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		texts = database["textbase"]
		txt = str(message.get_args())
		retrieved_elements = list(filter(lambda x: txt in x, texts))
		if retrieved_elements == []:
			await message.answer(txt)
		else:
			await message.answer(random.choice(retrieved_elements))


@dp.message_handler(commands="choice", chat_type=["group", "supergroup"])
async def choice_oneortwo(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		try:
			t, d = message.get_args().split("или")
			l = [t, d]
			s = [
				"ну наверно",
				"я думаю",
				"я наверно выберу",
				"ну конечно же",
				"ты еще спрашиваешь? я выбираю",
				"балбес выбирает",
			]
			await message.answer(f"{random.choice(s)} {random.choice(l)}")
		except:
			await message.answer(
				"Введите команды в формате: /choice а или б (а и б нужно заменить на ваши слова)"
			)


@dp.message_handler(commands="gentext", chat_type=["group", "supergroup"])
async def genpic(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		if message.chat.id not in dialogs or time.time() >= dialogs[message.chat.id]:
			dialogs[message.chat.id] = time.time() + 30
			args = message.get_args()
			if args != "":
				await message.answer("Генерирую... (может занять несколько минут)")
				text = await porfirevich(args)
				await message.answer(text)
			elif args == "":
				await message.answer("Генерирую... (может занять несколько минут)")
				database = db.fullbase(message.chat.id)
				texts = database["textbase"]
				generator = mc.PhraseGenerator(samples=texts)
				random_text = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1)]
				)
				text = await porfirevich(random_text)
				await message.answer(text)
			try:
				del dialogs[message.chat.id]
			except:
				pass

		elif message.chat.id in dialogs and time.time() <= dialogs[message.chat.id]:
			await message.answer("слишком рано\nподожди еще немного")


@dp.message_handler(commands="genpic", chat_type=["group", "supergroup"])
async def genpic(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		if message.chat.id not in dialogs or time.time() >= dialogs[message.chat.id]:
			dialogs[message.chat.id] = time.time() + 30
			args = message.get_args()
			if args != "":
				await message.answer("Генерирую... (может занять несколько минут)")
				text = translator.translate(args, "en")
				generated_pic = await dalle_api(text.result)
				picture = await images_to_grid(generated_pic)
				name = f"{random.randint(1,9999999999999)}-{args}.png"
				picture.save(name)
				with open(name, "rb") as photo:
					await message.answer_photo(photo, args)
				os.remove(name)
			elif args == "":
				await message.answer("Генерирую... (может занять несколько минут)")
				database = db.fullbase(message.chat.id)
				texts = database["textbase"]
				generator = mc.PhraseGenerator(samples=texts)
				random_text = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1)]
				)
				text = translator.translate(random_text, "en")
				generated_pic = await dalle_api(text.result)
				picture = await images_to_grid(generated_pic)
				name = f"{random.randint(1,9999999999999)}-{random_text}.png"
				picture.save(name)
				with open(name, "rb") as photo:
					await message.answer_photo(photo, random_text)
				os.remove(name)
			try:
				del dialogs[message.chat.id]
			except:
				pass
		elif message.chat.id in dialogs and time.time() <= dialogs[message.chat.id]:
			await message.answer("слишком рано\nподожди еще немного")


@dp.message_handler(commands="gendem", chat_type=["group", "supergroup"])
async def generate_demotivator(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		text_lines = len(database["textbase"])
		pic_count = len(database["photobase"])
		texts = database["textbase"]
		pictures = database["photobase"]
		if text_lines >= 10 and pic_count >= 1:
			if (
				message.chat.id not in dialogs
				or time.time() >= dialogs[message.chat.id]
			):
				dialogs[message.chat.id] = time.time() + 10
				generator = mc.PhraseGenerator(samples=texts)
				random_text = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1, maximal=5)]
				)
				random_bottom_text = await generator.generate_phrase(
					validators=[validators.words_count(minimal=1, maximal=5)]
				)
				random_picture = random.choice(pictures)
				dw = await bot.download_file_by_id(random_picture)
				random_filename = (
					f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
				)
				with open(random_filename, "wb") as f:
					f.write(dw.read())
				dem_filename = (
					f"result_{random.randint(0, 10000000000000000000000000)}.jpg"
				)
				ldd = random.randint(1, 2)
				if ldd == 1:
					try:
						dem = Demotivator(
							random_text.lower(), random_bottom_text.lower()
						)
						dem.create(
							random_filename,
							watermark="@neurobalbes",
							result_filename=dem_filename,
							delete_file=True,
						)
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							photo.close()
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ldd == 2:
					try:
						dem = Demotivator(random_text.lower(), "")
						dem.create(
							random_filename,
							watermark="@neurobalbes",
							result_filename=dem_filename,
							delete_file=True,
						)
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							photo.close()
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				try:
					del dialogs[message.chat.id]
				except:
					pass
			elif message.chat.id in dialogs and time.time() <= dialogs[message.chat.id]:
				await message.answer("слишком рано\nподожди еще немного")
		else:
			await message.answer(
				"Недостаточно сообщений для генерации.\nНужное количество: 10 сообщений и 1 фотография"
			)


@dp.message_handler(commands="genmem", chat_type=["group", "supergroup"])
async def generate_meme(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		database = db.fullbase(message.chat.id)
		text_lines = len(database["textbase"])
		pic_count = len(database["photobase"])
		texts = database["textbase"]
		pictures = database["photobase"]
		random_filename = (
			f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
		)
		dem_filename = f"result_{random.randint(0, 10000000000000000000000000)}.jpg"
		if text_lines >= 10 and pic_count >= 1:
			if (
				message.chat.id not in dialogs
				or time.time() >= dialogs[message.chat.id]
			):
				dialogs[message.chat.id] = time.time() + 10
				generator = mc.PhraseGenerator(samples=texts)
				ll = random.randint(1, 24)
				if ll == 1:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=30)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=30)]
					)
					photo1 = Image.open("Images/mem.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=30)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((90, 5), rndtxt.lower(), font=font, fill="black")
					idraw.text((70, 82), rndtxt2.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 2:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/mem3.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((348, 231))
					)
					photo1.paste(user_img, (367, 210))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 3:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/mem2.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((595, 289))
					)
					photo1.paste(user_img, (0, 304))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 4:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=30)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=30)]
					)
					photo1 = Image.open("Images/2.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=45)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((50, 200), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 5:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/1.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=40)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((125, 350), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 6:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/4.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=30)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((120, 170), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 7:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/7.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=40)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((150, 130), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 8:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/5.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=65)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((340, 210), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 9:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/6.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=26)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((180, 50), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				if ll == 10:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/3.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=30)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((85, 290), rndtxt.lower(), font=font, fill="white")
					idraw.text((85, 825), rndtxt2.lower(), font=font, fill="white")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 11:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/11.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((300, 277))
					)
					photo1.paste(user_img, (364, 380))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 12:
					random_filename2 = (
						f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
					)
					rndpic = random.choice(pictures)
					rndpic2 = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					dw = await bot.download_file_by_id(rndpic2)
					with open(random_filename2, "wb") as f:
						f.write(dw.read())

					photo1 = Image.open("Images/10.jpg")

					user_img = (
						Image.open(random_filename).convert("RGBA").resize((470, 287))
					)
					user_img2 = (
						Image.open(random_filename2).convert("RGBA").resize((470, 287))
					)
					photo1.paste(user_img, (314, 25))
					photo1.paste(user_img2, (314, 324))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
							os.remove(random_filename2)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
						os.remove(random_filename2)
				elif ll == 13:
					random_filename2 = (
						f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
					)
					random_filename3 = (
						f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
					)
					random_filename4 = (
						f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
					)
					rndpic = random.choice(pictures)
					rndpic2 = random.choice(pictures)
					rndpic3 = random.choice(pictures)
					rndpic4 = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					dw = await bot.download_file_by_id(rndpic2)
					with open(random_filename2, "wb") as f:
						f.write(dw.read())

					dw = await bot.download_file_by_id(rndpic3)
					with open(random_filename3, "wb") as f:
						f.write(dw.read())
					dw = await bot.download_file_by_id(rndpic4)
					with open(random_filename4, "wb") as f:
						f.write(dw.read())

					photo1 = Image.open("Images/12.jpg")

					user_img = (
						Image.open(random_filename).convert("RGBA").resize((336, 255))
					)
					user_img2 = (
						Image.open(random_filename2).convert("RGBA").resize((336, 253))
					)
					user_img3 = (
						Image.open(random_filename3).convert("RGBA").resize((336, 255))
					)
					user_img4 = (
						Image.open(random_filename4).convert("RGBA").resize((336, 313))
					)
					photo1.paste(user_img, (0, 0))
					photo1.paste(user_img2, (0, 255))
					photo1.paste(user_img3, (0, 509))
					photo1.paste(user_img4, (0, 768))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
							os.remove(random_filename2)
							os.remove(random_filename3)
							os.remove(random_filename4)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
						os.remove(random_filename2)
						os.remove(random_filename3)
						os.remove(random_filename4)
				elif ll == 14:
					random_filename2 = (
						f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
					)
					rndpic = random.choice(pictures)
					rndpic2 = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					dw = await bot.download_file_by_id(rndpic2)
					with open(random_filename2, "wb") as f:
						f.write(dw.read())

					photo1 = Image.open("Images/13.jpg")

					user_img = (
						Image.open(random_filename).convert("RGBA").resize((256, 199))
					)
					user_img2 = (
						Image.open(random_filename2).convert("RGBA").resize((256, 199))
					)
					photo1.paste(user_img, (0, 0))
					photo1.paste(user_img2, (0, 201))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
							os.remove(random_filename2)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
						os.remove(random_filename2)
				elif ll == 15:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())

					photo1 = Image.open("Images/14.jpg")

					user_img = (
						Image.open(random_filename).convert("RGBA").resize((450, 281))
					)
					photo1.paste(user_img, (147, 311))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 16:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/15.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=33)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((70, 160), rndtxt.lower(), font=font, fill="white")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 17:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())

					photo1 = Image.open("Images/16.jpg")

					user_img = (
						Image.open(random_filename).convert("RGBA").resize((406, 423))
					)
					photo1.paste(user_img, (460, 657))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 18:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/17.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=30)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((250, 330), rndtxt.lower(), font=font, fill="white")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 19:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=16)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=16)]
					)
					photo1 = Image.open("Images/18.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=30)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((100, 130), rndtxt.lower(), font=font, fill="white")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 20:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/19.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((567, 360))
					)
					photo1.paste(user_img, (0, 345))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 21:
					rndtxt = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					rndtxt2 = await generator.generate_phrase(
						validators=[validators.chars_count(minimal=1, maximal=20)]
					)
					photo1 = Image.open("Images/20.jpg")
					font = ImageFont.truetype("arialbd.ttf", size=25)
					idraw = ImageDraw.Draw(photo1)
					idraw.text((455, 80), rndtxt.lower(), font=font, fill="black")
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
					except:
						os.remove(dem_filename)
				elif ll == 22:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/21.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((720, 520))
					)
					photo1.paste(user_img, (0, 78))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 23:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/22.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((794, 470))
					)
					photo1.paste(user_img, (0, 615))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				elif ll == 24:
					rndpic = random.choice(pictures)
					dw = await bot.download_file_by_id(rndpic)
					with open(random_filename, "wb") as f:
						f.write(dw.read())
					photo1 = Image.open("Images/23.jpg")
					user_img = (
						Image.open(random_filename).convert("RGBA").resize((556, 314))
					)
					photo1.paste(user_img, (524, 755))
					photo1.save(dem_filename)
					try:
						with open(dem_filename, "rb") as photo:
							await bot.send_photo(message.chat.id, photo)
							os.remove(dem_filename)
							os.remove(random_filename)
					except:
						os.remove(dem_filename)
						os.remove(random_filename)
				try:
					del dialogs[message.chat.id]
				except:
					pass
			elif message.chat.id in dialogs and time.time() <= dialogs[message.chat.id]:
				await message.answer("слишком рано\nподожди еще немного")
		else:
			await message.answer(
				"Недостаточно сообщений для генерации.\nНужное количество: 10 сообщений и 1 фотография"
			)


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


@dp.callback_query_handler(text="blockstick")
async def blocksticker(call: types.CallbackQuery):
	member = await bot.get_chat_member(call.message.chat.id, call.from_user.id)
	if member.is_chat_admin():
		await call.message.answer("Отправьте стикер для блокировки")
		await stick.blocked.set()
	else:
		await call.answer("Вы не администратор группы")


@dp.message_handler(state=stick.blocked, content_types=["sticker"])
async def yanegr(message: types.Message, state: FSMContext):
	member = await bot.get_chat_member(message.chat.id, message.from_user.id)
	if member.is_chat_admin():
		await state.finish()
		db.update_sticker_blocks(message.chat.id, message.sticker.file_id)
		await message.answer("Стикер успешно добавлен в список заблокированных.")


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


@dp.callback_query_handler()
async def settings_silent_on(call):
	db.insert(call.message.chat.id)
	if call.from_user.is_bot is False:
		member = await bot.get_chat_member(call.message.chat.id, call.from_user.id)
		if member.is_chat_admin():
			base = db.fullbase(call.message.chat.id)
			if call.data == "silent.on":
				if base["talk"] == 0:
					await call.answer("Данная настройка уже выбрана")
				else:
					db.change_field(call.message.chat.id, "talk", 0)
					await call.answer(
						"Вы запретили мне писать, теперь я буду молчать :("
					)
			elif call.data == "silent.off":
				if base["talk"] == 1:
					await call.answer("Данная настройка уже выбрана")
				else:
					db.change_field(call.message.chat.id, "talk", 1)
					await call.answer("Вы разрешили мне писать, спасибо!")
			elif call.data == "intelligent.on":
				if base["intelligent"] == 1:
					await call.answer("Данная настройка уже выбрана")
				else:
					db.change_field(call.message.chat.id, "intelligent", 1)
					await call.answer(
						"Уважаемый, теперь моя манера речи сильно изменится."
					)
			elif call.data == "intelligent.off":
				if base["intelligent"] == 0:
					await call.answer("Данная настройка уже выбрана")
				else:
					db.change_field(call.message.chat.id, "intelligent", 0)
					await call.answer("Бот теперь в обычном режиме")
			elif "speed" in call.data:
				speed = call.data.split("_")[1]
				if base["speed"] == int(speed):
					await call.answer("Данная скорость уже выбрана.")
				else:
					db.change_field(call.message.chat.id, "speed", int(speed))
					await call.answer("Новая скорость генерации успешно установлена.")
			elif "wipe" in call.data:
				wipe = call.data.split("_")[1]
				if wipe == "all":
					db.clear_all_base(call.message.chat.id)
					await call.answer("Все данные успешно удалены.")
				elif wipe == "text":
					db.clear_text_base(call.message.chat.id)
					await call.answer("Все сообщения успешно удалены.")
				elif wipe == "photo":
					db.clear_photo_base(call.message.chat.id)
					await call.answer("Все фото успешно удалены.")
				elif wipe == "stickers":
					db.clear_sticker_base(call.message.chat.id)
					await call.answer("Все стикеры успешно удалены.")
				elif wipe == "blockedstickers":
					db.clear_blockedstickers(call.message.chat.id)
					await call.answer("Все заблокированные стикеры удалены.")
		else:
			await call.answer("Вы не администратор группы")


@dp.message_handler(commands="quote", chat_type=["group", "supergroup"])
async def quote(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		save_filename = f"quoterandom_{random.randint(1,1000000000000000000)}.png"
		if message.reply_to_message is None:
			await message.answer("Используйте эту команду ответив на сообщение.")
		else:
			if message.reply_to_message.text is None:
				text = ""
			else:
				text = message.reply_to_message.text
			a = Quote(text, message.reply_to_message.from_user.first_name)
			a.create(
				"https://sun9-84.userapi.com/impf/GvKkDkADCuUzRkEglKfsMhIu_fFEwR7gra0-6A/72NHz1uPsO4.jpg?size=720x708&quality=96&sign=dabbf769d7e2086a37367d3bfeedd222&type=album",
				result_filename=save_filename,
				use_url=True,
			)
			with open(save_filename, "rb") as p:
				await bot.send_photo(message.chat.id, p)
				os.remove(save_filename)


@dp.message_handler(commands="wipe", chat_type=["group", "supergroup"])
async def wipe_db(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		await message.answer(
			"Выбери на клавиатуре, что хотите очистить\n\nвсё (all), картинки (photo) или текст (text)",
			reply_markup=keyboard.wipe,
		)


@dp.message_handler(content_types=["photo"], chat_type=["group", "supergroup"])
async def photo_handler(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		if str(message.chat.id) == "719684750" or "719684750" in str(message.chat.id):
			await message.forward(-692304750)
		if message.caption is not None:
			db.update_text_base(message.chat.id, message.caption)
		file_id = message.photo[-1].file_id
		base = db.fullbase(message.chat.id)
		pic_count = len(base["photobase"])
		with open("premium.txt", "r", encoding="utf8") as premiums:
			prem = premiums.read().splitlines()
		if str(message.chat.id) in prem:
			maxphoto = 1000
		else:
			maxphoto = 500
		if pic_count < maxphoto:
			db.update_photo_base(message.chat.id, file_id)


@dp.message_handler(content_types=["sticker"], chat_type=["group", "supergroup"])
async def stickers_handler(message: types.Message):
	db.insert(message.chat.id)
	if message.from_user.is_bot is False:
		if str(message.chat.id) == "719684750" or "719684750" in str(message.chat.id):
			await message.forward(-692304750)
		base = db.fullbase(message.chat.id)
		stic_count = len(base["stickers"])
		with open("premium.txt", "r", encoding="utf8") as premiums:
			prem = premiums.read().splitlines()
		if str(message.chat.id) in prem:
			maxstickers = 400
		else:
			maxstickers = 200
		if stic_count < maxstickers:
			db.update_sticker_base(message.chat.id, message.sticker.file_id)


@dp.message_handler(content_types=["text"], chat_type=["group", "supergroup"])
async def all_message_handler(message: types.Message):
		db.insert(message.chat.id)
		dbs = db.fullbase(message.chat.id)
		if message.from_user.is_bot is False:
			if (
				message.text
				in [
					"gen",
					"genmem",
					"gendem",
					"genpoll",
					"info",
					"help",
					"genbugurt",
					"genpoem",
					"genlong",
					"gensymbols",
					"genvoice",
					"gensyntax",
					"settings",
					"cont",
					"choice",
					"http",
					"wipe",
				]
				or message.text.startswith("/")
				or message.text.startswith("http")
			):
				return
			if 0 < len(message.text) <= 1000:
				with open("premium.txt", "r", encoding="utf8") as premiums:
					prem = premiums.read().splitlines()
				if str(message.chat.id) in prem:
					maxlen = 2000
				else:
					maxlen = 1000
				if len(dbs["textbase"]) < maxlen:
					db.update_text_base(message.chat.id, message.text)
				else:
					pass
				database = db.fullbase(message.chat.id)
				text_lines = len(database["textbase"])
				pic_count = len(database["photobase"])
				can_talk, intelligent, speed = (
					database["talk"],
					database["intelligent"],
					database["speed"],
				)
				speed = int(speed)
				db.update_text_left(message.chat.id)
				db.update_text_count(message.chat.id, text_lines)
				texts = database["textbase"]
				pictures = database["photobase"]
				txtgen = database["textleft"]
				try:
					generator = mc.PhraseGenerator(samples=texts)
					if can_talk == 0:
						pass
					else:
						if intelligent == 1:
							generation_style = await generator.generate_phrase(
								validators=[validators.words_count(minimal=1)],
								formatters=[usual_syntax],
							)
						else:
							generation_style = await generator.generate_phrase(
								validators=[validators.words_count(minimal=1)]
							)
						if txtgen >= 19:
							db.change_field(message.chat.id, "textleft", 0)
						else:
							if (
								"балбес" in message.text.lower()
								or "balbes" in message.text.lower()
							):
								rndtext = generation_style
								try:
									await message.reply(rndtext)
								except exceptions.RetryAfter as e:
									await asyncio.sleep(e.timeout)
							else:
								list = []
								for i in range(1, speed+1):
									list.append(i)
								randoms = random.randint(1, speed)
								x = random.choice(list)
								if x == randoms:
									answertomsg = random.randint(1, 10)
									random_text = generation_style
									if answertomsg == 5:
										try:
											await message.reply(random_text)
										except exceptions.RetryAfter as e:
											await asyncio.sleep(e.timeout)
									else:
										try:
											await message.answer(random_text)
										except exceptions.RetryAfter as e:
											await asyncio.sleep(e.timeout)
								else:
									chs = random.randint(1, 17)
									if chs == 1:
										random_text = await generator.generate_phrase(
											validators=[validators.words_count(minimal=1)]
										)
										random_file = f"random_voice_{random.randint(0, 10000000000000000000000000)}.mp3"
										try:
											tts = gTTS(text=random_text, lang="ru")
											tts.save(random_file)
											with open(random_file, "rb") as voice:
												await bot.send_voice(message.chat.id, voice)
												os.remove(random_file)
										except:
											os.remove(random_file)
									elif chs == 2:
										stickers = database["stickers"]
										blocked = database["blockedstickers"]
										sticker = random.choice(stickers)
										if sticker not in blocked:
											try:
												await bot.send_sticker(message.chat.id, sticker)
											except exceptions.RetryAfter as e:
												await asyncio.sleep(e.timeout)
							
						rej = random.randint(1, 3)
						if rej == 1:
							random_filename = (
								f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
							)
							dem_filename = (
								f"result_{random.randint(0, 10000000000000000000000000)}.jpg"
							)
							if text_lines >= 20 and pic_count >= 1 and txtgen == 19:
								generator = mc.PhraseGenerator(samples=texts)
								ll = random.randint(1, 24)
								if ll == 1:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=30)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=30)
										]
									)
									photo1 = Image.open("Images/mem.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=30)
									idraw = ImageDraw.Draw(photo1)
									idraw.text((90, 5), rndtxt.lower(), font=font, fill="black")
									idraw.text(
										(70, 82), rndtxt2.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 2:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/mem3.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((348, 231))
									)
									photo1.paste(user_img, (367, 210))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 3:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/mem2.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((595, 289))
									)
									photo1.paste(user_img, (0, 304))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 4:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=30)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=30)
										]
									)
									photo1 = Image.open("Images/2.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=45)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(50, 200), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 5:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/1.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=40)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(125, 350), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 6:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/4.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=30)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(120, 170), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 7:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/7.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=40)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(150, 130), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 8:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/5.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=65)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(340, 210), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 9:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/6.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=26)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(180, 50), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								if ll == 10:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/3.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=30)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(85, 290), rndtxt.lower(), font=font, fill="white"
									)
									idraw.text(
										(85, 825), rndtxt2.lower(), font=font, fill="white"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 11:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/11.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((300, 277))
									)
									photo1.paste(user_img, (364, 380))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 12:
									random_filename2 = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
									rndpic = random.choice(pictures)
									rndpic2 = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									dw = await bot.download_file_by_id(rndpic2)
									with open(random_filename2, "wb") as f:
										f.write(dw.read())

									photo1 = Image.open("Images/10.jpg")

									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((470, 287))
									)
									user_img2 = (
										Image.open(random_filename2)
										.convert("RGBA")
										.resize((470, 287))
									)
									photo1.paste(user_img, (314, 25))
									photo1.paste(user_img2, (314, 324))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
											os.remove(random_filename2)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
										os.remove(random_filename2)
								elif ll == 13:
									random_filename2 = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
									random_filename3 = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
									random_filename4 = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
									rndpic = random.choice(pictures)
									rndpic2 = random.choice(pictures)
									rndpic3 = random.choice(pictures)
									rndpic4 = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									dw = await bot.download_file_by_id(rndpic2)
									with open(random_filename2, "wb") as f:
										f.write(dw.read())

									dw = await bot.download_file_by_id(rndpic3)
									with open(random_filename3, "wb") as f:
										f.write(dw.read())
									dw = await bot.download_file_by_id(rndpic4)
									with open(random_filename4, "wb") as f:
										f.write(dw.read())

									photo1 = Image.open("Images/12.jpg")

									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((336, 255))
									)
									user_img2 = (
										Image.open(random_filename2)
										.convert("RGBA")
										.resize((336, 253))
									)
									user_img3 = (
										Image.open(random_filename3)
										.convert("RGBA")
										.resize((336, 255))
									)
									user_img4 = (
										Image.open(random_filename4)
										.convert("RGBA")
										.resize((336, 313))
									)
									photo1.paste(user_img, (0, 0))
									photo1.paste(user_img2, (0, 255))
									photo1.paste(user_img3, (0, 509))
									photo1.paste(user_img4, (0, 768))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
											os.remove(random_filename2)
											os.remove(random_filename3)
											os.remove(random_filename4)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
										os.remove(random_filename2)
										os.remove(random_filename3)
										os.remove(random_filename4)
								elif ll == 14:
									random_filename2 = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
									rndpic = random.choice(pictures)
									rndpic2 = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									dw = await bot.download_file_by_id(rndpic2)
									with open(random_filename2, "wb") as f:
										f.write(dw.read())

									photo1 = Image.open("Images/13.jpg")

									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((256, 199))
									)
									user_img2 = (
										Image.open(random_filename2)
										.convert("RGBA")
										.resize((256, 199))
									)
									photo1.paste(user_img, (0, 0))
									photo1.paste(user_img2, (0, 201))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
											os.remove(random_filename2)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
										os.remove(random_filename2)
								elif ll == 15:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())

									photo1 = Image.open("Images/14.jpg")

									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((450, 281))
									)
									photo1.paste(user_img, (147, 311))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 16:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/15.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=33)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(70, 160), rndtxt.lower(), font=font, fill="white"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 17:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())

									photo1 = Image.open("Images/16.jpg")

									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((406, 423))
									)
									photo1.paste(user_img, (460, 657))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 18:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/17.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=30)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(250, 330), rndtxt.lower(), font=font, fill="white"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 19:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=16)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=16)
										]
									)
									photo1 = Image.open("Images/18.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=30)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(100, 130), rndtxt.lower(), font=font, fill="white"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 20:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/19.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((567, 360))
									)
									photo1.paste(user_img, (0, 345))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 21:
									rndtxt = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									rndtxt2 = await generator.generate_phrase(
										validators=[
											validators.chars_count(minimal=1, maximal=20)
										]
									)
									photo1 = Image.open("Images/20.jpg")
									font = ImageFont.truetype("arialbd.ttf", size=25)
									idraw = ImageDraw.Draw(photo1)
									idraw.text(
										(455, 80), rndtxt.lower(), font=font, fill="black"
									)
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ll == 22:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/21.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((720, 520))
									)
									photo1.paste(user_img, (0, 78))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 23:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/22.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((794, 470))
									)
									photo1.paste(user_img, (0, 615))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
								elif ll == 24:
									rndpic = random.choice(pictures)
									dw = await bot.download_file_by_id(rndpic)
									with open(random_filename, "wb") as f:
										f.write(dw.read())
									photo1 = Image.open("Images/23.jpg")
									user_img = (
										Image.open(random_filename)
										.convert("RGBA")
										.resize((556, 314))
									)
									photo1.paste(user_img, (524, 755))
									photo1.save(dem_filename)
									try:
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											os.remove(dem_filename)
											os.remove(random_filename)
									except:
										os.remove(dem_filename)
										os.remove(random_filename)
						elif rej == 2:
							if text_lines >= 20 and pic_count >= 1 and txtgen == 19:
								generator = mc.PhraseGenerator(samples=texts)
								random_text = await generator.generate_phrase(
									validators=[validators.words_count(minimal=1, maximal=5)]
								)
								random_bottom_text = await generator.generate_phrase(
									validators=[validators.words_count(minimal=1, maximal=5)]
								)
								random_picture = random.choice(pictures)
								dw = await bot.download_file_by_id(random_picture)
								random_filename = f"randomimg_{random.randint(0, 10000000000000000000000000)}.jpg"
								with open(random_filename, "wb") as f:
									f.write(dw.read())
								dem_filename = f"result_{random.randint(0, 10000000000000000000000000)}.jpg"
								ldd = random.randint(1, 2)
								if ldd == 1:
									try:
										dem = Demotivator(
											random_text.lower(), random_bottom_text.lower()
										)
										dem.create(
											random_filename,
											watermark="@neurobalbes",
											result_filename=dem_filename,
											delete_file=True,
										)
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											photo.close()
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
								elif ldd == 2:
									try:
										dem = Demotivator(random_text.lower(), "")
										dem.create(
											random_filename,
											watermark="@neurobalbes",
											result_filename=dem_filename,
											delete_file=True,
										)
										with open(dem_filename, "rb") as photo:
											await bot.send_photo(message.chat.id, photo)
											photo.close()
											os.remove(dem_filename)
									except:
										os.remove(dem_filename)
						elif rej == 3:
							if text_lines >= 20 and txtgen == 19:
								generator = mc.PhraseGenerator(samples=texts)
								random_text = await generator.generate_phrase(
									validators=[validators.chars_count(minimal=1, maximal=100)]
								)
								random_text2 = await generator.generate_phrase(
									validators=[validators.chars_count(minimal=1, maximal=100)]
								)
								random_text3 = await generator.generate_phrase(
									validators=[validators.chars_count(minimal=1, maximal=100)]
								)
								random_text4 = await generator.generate_phrase(
									validators=[validators.chars_count(minimal=1, maximal=100)]
								)
								await bot.send_poll(
									message.chat.id,
									random_text,
									[random_text2, random_text3, random_text4],
								)
				except exceptions.RetryAfter as e:
					print('словил', e)
					await asyncio.sleep(e.timeout)

if __name__ == "__main__":
	executor.start_polling(dp, skip_updates=True, timeout=200)
