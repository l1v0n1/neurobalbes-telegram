import sqlite3


connection = sqlite3.connect("data.db")
q = connection.cursor()


def insert(peerid):
	q.execute(
		"""CREATE TABLE IF NOT EXISTS peer{} (
		peer_id INT DEFAULT {}, 
		talk INT DEFAULT 1, 
		intelligent INT DEFAULT 0, 
		speed INT DEFAULT 3, 
		textleft INT DEFAULT 0,
		textcount INT DEFAULT 0,
		textbase TEXT,
		photobase TEXT,
		stickers TEXT,
		blockedstickers TEXT
		)""".format(
			str(peerid).replace('-', ''), str(peerid).replace('-', '')
		)
	)
	cursor = q.execute("SELECT * FROM peer{}".format(str(peerid).replace('-', '')))

	
	if cursor.fetchall() == [] or cursor.fetchall() is None:
		q.execute(
			"INSERT INTO peer{} (peer_id, talk, intelligent, speed, textleft, textcount) VALUES (?, ?, ?, ?, ?, ?)".format(
				str(peerid).replace('-', '')
			),
			(str(peerid).replace('-', ''), 1, 0, 3, 0, 0),
		)
	connection.commit()


def fullbase(peerid):
	cursor = q.execute("SELECT * FROM peer{}".format(str(peerid).replace('-', '')))
	texts = []
	photos = []
	stickers = []
	blockedstickers = []
	for row in cursor:
		textbase = row[6]
		photobase = row[7]
		sticks = row[8]
		blsticks = row[9]
		texts.append(textbase)
		photos.append(photobase)
		stickers.append(sticks)
		blockedstickers.append(blsticks)
	data = q.execute("SELECT * FROM peer{}".format(str(peerid).replace('-', ''))).fetchall()
	data = data[0]
	chat_id = data[0]
	talk = data[1]
	intelligent = data[2]
	speed = data[3]
	textleft = data[4]
	textcount = data[5]
	return dict(
		peer_id=chat_id,
		talk=talk,
		intelligent=intelligent,
		speed=speed,
		textleft=textleft,
		textcount=textcount,
		textbase=[i for i in texts if i is not None],
		photobase=[i for i in photos if i is not None],
		stickers=[i for i in stickers if i is not None],
		blockedstickers=[i for i in blockedstickers if i is not None]
	)


def update_text_base(peerid, text):
	q.execute("INSERT INTO peer{} (textbase) VALUES (?)".format(str(peerid).replace('-', '')), (text,))
	connection.commit()


def clear_text_base(peerid):
	q.execute("UPDATE peer{} SET textbase = Null".format(str(peerid).replace('-', '')))
	connection.commit()


def update_photo_base(peerid, photo):
	q.execute("INSERT INTO peer{} (photobase) VALUES (?)".format(str(peerid).replace('-', '')), (photo,))
	connection.commit()


def clear_photo_base(peerid):
	q.execute("UPDATE peer{} SET photobase = Null".format(str(peerid).replace('-', '')))
	connection.commit()


def clear_all_base(peerid):
	q.execute("UPDATE peer{} SET textbase = Null".format(str(peerid).replace('-', '')))
	q.execute("UPDATE peer{} SET photobase = Null".format(str(peerid).replace('-', '')))
	q.execute("UPDATE peer{} SET stickers = Null".format(str(peerid).replace('-', '')))
	connection.commit()


def change_field(peerid, field, key):
	q.execute("UPDATE peer{} SET {} = {}".format(str(peerid).replace('-', ''), field, key))
	connection.commit()


def update_text_count(peerid, count):
	q.execute("UPDATE peer{} SET textcount = {}".format(str(peerid).replace('-', ''), count))
	connection.commit()


def update_text_left(peerid):
	q.execute("UPDATE peer{} SET textleft = textleft+1".format(str(peerid).replace('-', '')))
	connection.commit()


def sender():
	cursor = q.execute("SELECT name FROM sqlite_master WHERE type='table';")
	return cursor.fetchall()


def update_sticker_base(peerid, sticker):
	q.execute("INSERT INTO peer{} (stickers) VALUES (?)".format(str(peerid).replace('-', '')), (sticker,))
	connection.commit()


def update_sticker_blocks(peerid, sticker):
	q.execute("INSERT INTO peer{} (blockedstickers) VALUES (?)".format(str(peerid).replace('-', '')), (sticker,))
	connection.commit()


def clear_sticker_base(peerid):
	q.execute("UPDATE peer{} SET stickers = Null".format(str(peerid).replace('-', '')))
	connection.commit()


def clear_blockedstickers(peerid):
	q.execute("UPDATE peer{} SET blockedstickers = Null".format(str(peerid).replace('-', '')))
	connection.commit()


def add_new_field():
	all = q.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
	for i in all:
		peer = i[0].split('peer')[1]
		q.execute("ALTER TABLE peer{} ADD COLUMN nextgen INT;".format(peer))
	connection.commit()
