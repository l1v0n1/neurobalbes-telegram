import sqlite3
import json
import threading
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('database')

# Thread-local storage for database connections
local_storage = threading.local()

# Database file path
DB_FILE = "app/database/data.db"

# Connection pool lock
_lock = threading.Lock()

@contextmanager
def get_connection():
	"""Get a database connection from the pool or create a new one."""
	if not hasattr(local_storage, 'connection'):
		with _lock:
			local_storage.connection = sqlite3.connect(DB_FILE)
			# Enable foreign keys
			local_storage.connection.execute("PRAGMA foreign_keys = ON")
			# Optimize database
			local_storage.connection.execute("PRAGMA journal_mode = WAL")
			local_storage.connection.execute("PRAGMA synchronous = NORMAL")
			local_storage.connection.execute("PRAGMA cache_size = 10000")
			local_storage.connection.execute("PRAGMA temp_store = MEMORY")
	
	try:
		# Set row factory to return dictionaries
		local_storage.connection.row_factory = sqlite3.Row
		yield local_storage.connection
	except sqlite3.Error as e:
		logger.error(f"Database error: {e}")
		if local_storage.connection:
			local_storage.connection.rollback()
		raise
	except Exception as e:
		logger.error(f"Unexpected error: {e}")
		if local_storage.connection:
			local_storage.connection.rollback()
		raise

def init_db():
	"""Initialize the database schema."""
	with get_connection() as conn:
		cursor = conn.cursor()
		
		# Create chats table
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS chats (
			id INTEGER PRIMARY KEY,
			peer_id TEXT UNIQUE NOT NULL,
			talk INTEGER DEFAULT 1,
			intelligent INTEGER DEFAULT 0,
			speed INTEGER DEFAULT 3,
			textleft INTEGER DEFAULT 0,
			textcount INTEGER DEFAULT 0,
			nextgen INTEGER DEFAULT 0,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
		""")
		
		# Create texts table with foreign key to chats
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS texts (
			id INTEGER PRIMARY KEY,
			chat_id INTEGER NOT NULL,
			text TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
		)
		""")
		
		# Create photos table with foreign key to chats
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS photos (
			id INTEGER PRIMARY KEY,
			chat_id INTEGER NOT NULL,
			photo_id TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
		)
		""")
		
		# Create stickers table with foreign key to chats
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS stickers (
			id INTEGER PRIMARY KEY,
			chat_id INTEGER NOT NULL,
			sticker_id TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
		)
		""")
		
		# Create blocked_stickers table with foreign key to chats
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS blocked_stickers (
			id INTEGER PRIMARY KEY,
			chat_id INTEGER NOT NULL,
			sticker_id TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
		)
		""")
		
		# Create indexes for faster queries
		cursor.execute("CREATE INDEX IF NOT EXISTS idx_texts_chat_id ON texts(chat_id)")
		cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_chat_id ON photos(chat_id)")
		cursor.execute("CREATE INDEX IF NOT EXISTS idx_stickers_chat_id ON stickers(chat_id)")
		cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocked_stickers_chat_id ON blocked_stickers(chat_id)")
		
		conn.commit()

# Initialize database on module import
init_db()

def migrate_old_data():
	"""Migrate data from old table structure to new structure."""
	with get_connection() as conn:
		cursor = conn.cursor()
		
		# Get all tables from old structure
		old_tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'peer%'").fetchall()
		
		for table in old_tables:
			table_name = table[0]
			peer_id = table_name.replace('peer', '')
			
			try:
				# Get data from old table
				old_data = cursor.execute(f"SELECT * FROM {table_name}").fetchone()
				
				if old_data:
					# Insert into new chats table
					cursor.execute(
						"INSERT OR IGNORE INTO chats (peer_id, talk, intelligent, speed, textleft, textcount) VALUES (?, ?, ?, ?, ?, ?)",
						(peer_id, old_data['talk'], old_data['intelligent'], old_data['speed'], old_data['textleft'], old_data['textcount'])
					)
					
					# Get the new chat_id
					chat_id = cursor.execute("SELECT id FROM chats WHERE peer_id = ?", (peer_id,)).fetchone()['id']
					
					# Migrate text data
					text_data = cursor.execute(f"SELECT textbase FROM {table_name} WHERE textbase IS NOT NULL").fetchall()
					for text_row in text_data:
						if text_row['textbase']:
							cursor.execute(
								"INSERT INTO texts (chat_id, text) VALUES (?, ?)",
								(chat_id, text_row['textbase'])
							)
					
					# Migrate photo data
						photo_data = cursor.execute(f"SELECT photobase FROM {table_name} WHERE photobase IS NOT NULL").fetchall()
						for photo_row in photo_data:
							if photo_row['photobase']:
								cursor.execute(
									"INSERT INTO photos (chat_id, photo_id) VALUES (?, ?)",
									(chat_id, photo_row['photobase'])
								)
					
					# Migrate sticker data
					sticker_data = cursor.execute(f"SELECT stickers FROM {table_name} WHERE stickers IS NOT NULL").fetchall()
					for sticker_row in sticker_data:
						if sticker_row['stickers']:
							cursor.execute(
								"INSERT INTO stickers (chat_id, sticker_id) VALUES (?, ?)",
								(chat_id, sticker_row['stickers'])
							)
					
					# Migrate blocked sticker data
					blocked_sticker_data = cursor.execute(f"SELECT blockedstickers FROM {table_name} WHERE blockedstickers IS NOT NULL").fetchall()
					for blocked_row in blocked_sticker_data:
						if blocked_row['blockedstickers']:
							cursor.execute(
								"INSERT INTO blocked_stickers (chat_id, sticker_id) VALUES (?, ?)",
								(chat_id, blocked_row['blockedstickers'])
							)
			except Exception as e:
				logger.error(f"Error migrating data for {table_name}: {e}")
				continue
		
		conn.commit()

def insert(peer_id):
	"""Insert a new chat or get existing one."""
	peer_id = str(peer_id).replace('-', '')
	
	with get_connection() as conn:
		cursor = conn.cursor()
		
		# Check if chat exists
		chat = cursor.execute("SELECT id FROM chats WHERE peer_id = ?", (peer_id,)).fetchone()
		
		if not chat:
			# Insert new chat
			cursor.execute(
				"INSERT INTO chats (peer_id, talk, intelligent, speed, textleft, textcount) VALUES (?, ?, ?, ?, ?, ?)",
				(peer_id, 1, 0, 3, 0, 0)
			)
			conn.commit()
			return cursor.lastrowid
		else:
			return chat['id']

def get_chat_id(peer_id):
	"""Get chat ID from peer_id."""
	peer_id = str(peer_id).replace('-', '')
	
	with get_connection() as conn:
		cursor = conn.cursor()
		chat = cursor.execute("SELECT id FROM chats WHERE peer_id = ?", (peer_id,)).fetchone()
		
		if chat:
			return chat['id']
		else:
			return insert(peer_id)

def fullbase(peer_id):
	"""Get all data for a chat."""
	peer_id = str(peer_id).replace('-', '')
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		
		# Get chat data
		chat_data = cursor.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
		
		if not chat_data:
			return None
		
		# Get texts
		texts = cursor.execute("SELECT text FROM texts WHERE chat_id = ?", (chat_id,)).fetchall()
		text_list = [row['text'] for row in texts if row['text']]
		
		# Get photos
		photos = cursor.execute("SELECT photo_id FROM photos WHERE chat_id = ?", (chat_id,)).fetchall()
		photo_list = [row['photo_id'] for row in photos if row['photo_id']]
		
		# Get stickers
		stickers = cursor.execute("SELECT sticker_id FROM stickers WHERE chat_id = ?", (chat_id,)).fetchall()
		sticker_list = [row['sticker_id'] for row in stickers if row['sticker_id']]
		
		# Get blocked stickers
		blocked_stickers = cursor.execute("SELECT sticker_id FROM blocked_stickers WHERE chat_id = ?", (chat_id,)).fetchall()
		blocked_list = [row['sticker_id'] for row in blocked_stickers if row['sticker_id']]
		
		# Return as dictionary
		return {
			'peer_id': chat_data['peer_id'],
			'talk': chat_data['talk'],
			'intelligent': chat_data['intelligent'],
			'speed': chat_data['speed'],
			'textleft': chat_data['textleft'],
			'textcount': chat_data['textcount'],
			'textbase': text_list,
			'photobase': photo_list,
			'stickers': sticker_list,
			'blockedstickers': blocked_list
		}

def update_text_base(peer_id, text):
	"""Add text to a chat's text base."""
	if not text:
		return
		
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO texts (chat_id, text) VALUES (?, ?)", (chat_id, text))
		conn.commit()

def clear_text_base(peer_id):
	"""Clear all texts for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM texts WHERE chat_id = ?", (chat_id,))
		conn.commit()

def update_photo_base(peer_id, photo):
	"""Add photo to a chat's photo base."""
	if not photo:
		return
		
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO photos (chat_id, photo_id) VALUES (?, ?)", (chat_id, photo))
		conn.commit()

def clear_photo_base(peer_id):
	"""Clear all photos for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM photos WHERE chat_id = ?", (chat_id,))
		conn.commit()

def clear_all_base(peer_id):
	"""Clear all data for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM texts WHERE chat_id = ?", (chat_id,))
		cursor.execute("DELETE FROM photos WHERE chat_id = ?", (chat_id,))
		cursor.execute("DELETE FROM stickers WHERE chat_id = ?", (chat_id,))
		conn.commit()

def change_field(peer_id, field, value):
	"""Update a field in the chats table."""
	chat_id = get_chat_id(peer_id)
	
	# Validate field to prevent SQL injection
	valid_fields = ['talk', 'intelligent', 'speed', 'textleft', 'textcount', 'nextgen']
	if field not in valid_fields:
		logger.error(f"Invalid field: {field}")
		return
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute(f"UPDATE chats SET {field} = ? WHERE id = ?", (value, chat_id))
		conn.commit()

def update_text_count(peer_id, count):
	"""Update text count for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE chats SET textcount = ? WHERE id = ?", (count, chat_id))
		conn.commit()

def update_text_left(peer_id):
	"""Increment textleft for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("UPDATE chats SET textleft = textleft + 1 WHERE id = ?", (chat_id,))
		conn.commit()

def sender():
	"""Get all chats."""
	with get_connection() as conn:
		cursor = conn.cursor()
		chats = cursor.execute("SELECT peer_id FROM chats").fetchall()
		return [(chat['peer_id'],) for chat in chats]

def update_sticker_base(peer_id, sticker):
	"""Add sticker to a chat's sticker base."""
	if not sticker:
		return
		
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO stickers (chat_id, sticker_id) VALUES (?, ?)", (chat_id, sticker))
		conn.commit()

def update_sticker_blocks(peer_id, sticker):
	"""Add sticker to a chat's blocked stickers."""
	if not sticker:
		return
		
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO blocked_stickers (chat_id, sticker_id) VALUES (?, ?)", (chat_id, sticker))
		conn.commit()

def clear_sticker_base(peer_id):
	"""Clear all stickers for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM stickers WHERE chat_id = ?", (chat_id,))
		conn.commit()

def clear_blockedstickers(peer_id):
	"""Clear all blocked stickers for a chat."""
	chat_id = get_chat_id(peer_id)
	
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM blocked_stickers WHERE chat_id = ?", (chat_id,))
		conn.commit()

def add_new_field(field_name, default_value=None):
	"""Add a new field to the chats table."""
	with get_connection() as conn:
		cursor = conn.cursor()
		
		# Check if field exists
		columns = cursor.execute("PRAGMA table_info(chats)").fetchall()
		column_names = [col['name'] for col in columns]
		
		if field_name not in column_names:
			default_clause = f"DEFAULT {default_value}" if default_value is not None else ""
			cursor.execute(f"ALTER TABLE chats ADD COLUMN {field_name} INTEGER {default_clause}")
			conn.commit()

def get_chat_stats():
	"""Get statistics about the database."""
	with get_connection() as conn:
		cursor = conn.cursor()
		
		stats = {
			'total_chats': cursor.execute("SELECT COUNT(*) FROM chats").fetchone()[0],
			'total_texts': cursor.execute("SELECT COUNT(*) FROM texts").fetchone()[0],
			'total_photos': cursor.execute("SELECT COUNT(*) FROM photos").fetchone()[0],
			'total_stickers': cursor.execute("SELECT COUNT(*) FROM stickers").fetchone()[0],
			'total_blocked_stickers': cursor.execute("SELECT COUNT(*) FROM blocked_stickers").fetchone()[0],
			'db_size_kb': cursor.execute("SELECT page_count * page_size / 1024 FROM pragma_page_count(), pragma_page_size()").fetchone()[0]
		}
		
		return stats

def optimize_database():
	"""Оптимизирует базу данных для улучшения производительности."""
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("VACUUM")
		cursor.execute("ANALYZE")
		conn.commit()
	return True

def get_total_chats_count():
	"""Возвращает общее количество чатов в базе данных."""
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT COUNT(*) FROM chats")
		return cursor.fetchone()[0]

def get_total_phrases_count():
	"""Возвращает общее количество фраз во всех чатах."""
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT COUNT(*) FROM texts")
		return cursor.fetchone()[0]
