from subprocess import call
from aiogram import types
from config import channel, add_to_chat_link, chat, donate


help = types.InlineKeyboardMarkup(row_width=2)
help.add(
	types.InlineKeyboardButton(text='Добавить в чат', url=add_to_chat_link),
	types.InlineKeyboardButton(text='Канал бота', url=channel),
    types.InlineKeyboardButton(text='Группа бота', url=chat),
    types.InlineKeyboardButton(text='Помощь', url='https://telegra.ph/FAQ-01-16-7'),
    types.InlineKeyboardButton(text='Поддержать бота', url=donate)
	)


bset = types.InlineKeyboardMarkup(row_width=10)
bset.add(
    types.InlineKeyboardButton(text='silent.on', callback_data='silent.on'),
    types.InlineKeyboardButton(text='silent.off', callback_data='silent.off')
    )
bset.row()
bset.add(
    types.InlineKeyboardButton(text='intelligent.on', callback_data='intelligent.on'),
    types.InlineKeyboardButton(text='intelligent.off', callback_data='intelligent.off')
)
bset.row()
bset.add(
    types.InlineKeyboardButton(text='speed 1', callback_data='speed_1'),
    types.InlineKeyboardButton(text='speed 2', callback_data='speed_2'),
    types.InlineKeyboardButton(text='speed 3', callback_data='speed_3'))
bset.row()
bset.add(
    types.InlineKeyboardButton(text='speed 4', callback_data='speed_4'),
    types.InlineKeyboardButton(text='speed 5', callback_data='speed_5'),
    types.InlineKeyboardButton(text='speed 6', callback_data='speed_6')
)
bset.add(types.InlineKeyboardButton(text='Заблокировать стикер', callback_data='blockstick'))


silentoff = types.InlineKeyboardMarkup(row_width=1)
silentoff.add(types.InlineKeyboardButton(text='silent.off', callback_data='silent.off'))


wipe = types.InlineKeyboardMarkup(row_width=3)
wipe.add(
    types.InlineKeyboardButton(text='all', callback_data='wipe_all'),
    types.InlineKeyboardButton(text='text', callback_data='wipe_text'),
    types.InlineKeyboardButton(text='photo', callback_data='wipe_photo'),
    types.InlineKeyboardButton(text='stickers', callback_data='wipe_stickers'),
    types.InlineKeyboardButton(text='blocked stickers', callback_data='wipe_blockedstickers')
    )


apanel = types.InlineKeyboardMarkup(row_width=3)
apanel.add(
	types.InlineKeyboardButton(text='Рассылка', callback_data='admin_rass'),
	types.InlineKeyboardButton(text='Статистика', callback_data='admin_stats')
    )


back = types.ReplyKeyboardMarkup(resize_keyboard=True)
back.add(
    types.KeyboardButton('Отмена')
)
