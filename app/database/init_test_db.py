#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import time
import random
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("init_test_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('init_test_db')

def create_database():
    """Create a new database with the required tables."""
    # Remove existing database if it exists
    if os.path.exists("data.db"):
        os.remove("data.db")
        logger.info("Removed existing database")
    
    # Create a new database
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create users table
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        chat_id INTEGER UNIQUE,
        created_at INTEGER
    )
    """)
    
    # Create events table
    cursor.execute("""
    CREATE TABLE events (
        id INTEGER PRIMARY KEY,
        title TEXT,
        creator_id INTEGER,
        date INTEGER,
        location TEXT,
        description TEXT,
        status TEXT,
        FOREIGN KEY (creator_id) REFERENCES users (id)
    )
    """)
    
    # Create participants table
    cursor.execute("""
    CREATE TABLE participants (
        id INTEGER PRIMARY KEY,
        event_id INTEGER,
        user_id INTEGER,
        status TEXT,
        joined_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY (event_id) REFERENCES events (id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE (event_id, user_id)
    )
    """)
    
    # Create messages table
    cursor.execute("""
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY,
        event_id INTEGER,
        user_id INTEGER,
        content TEXT,
        timestamp INTEGER,
        FOREIGN KEY (event_id) REFERENCES events (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("Created database with tables: users, events, participants, messages")

def generate_test_data(num_users=1000, num_events=50, max_participants_per_event=200, num_messages=500):
    """Generate test data for the database."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Generate users
    logger.info(f"Generating {num_users} users...")
    for i in range(1, num_users + 1):
        cursor.execute(
            "INSERT INTO users (id, username, chat_id, created_at) VALUES (?, ?, ?, ?)",
            (i, f"user_{i}", 1000000 + i, int(time.time()))
        )
    
    # Generate events
    logger.info(f"Generating {num_events} events...")
    for i in range(1, num_events + 1):
        creator_id = random.randint(1, num_users)
        cursor.execute(
            "INSERT INTO events (id, title, creator_id, date, location, description, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                i,
                f"Event {i}",
                creator_id,
                int(time.time()) + random.randint(86400, 2592000),  # 1-30 days in the future
                f"Location {i}",
                f"Description for event {i}",
                random.choice(["active", "cancelled", "completed"])
            )
        )
    
    # Generate participants
    logger.info("Generating participants...")
    participant_id = 1
    for event_id in range(1, num_events + 1):
        num_participants = random.randint(10, min(max_participants_per_event, num_users))
        event_participants = random.sample(range(1, num_users + 1), num_participants)
        
        for user_id in event_participants:
            cursor.execute(
                "INSERT INTO participants (id, event_id, user_id, status, joined_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    participant_id,
                    event_id,
                    user_id,
                    random.choice(["confirmed", "pending", "declined"]),
                    int(time.time()),
                    int(time.time())
                )
            )
            participant_id += 1
    
    # Generate messages
    logger.info(f"Generating {num_messages} messages...")
    for i in range(1, num_messages + 1):
        event_id = random.randint(1, num_events)
        
        # Get a random participant for this event
        cursor.execute("SELECT user_id FROM participants WHERE event_id = ?", (event_id,))
        participants = cursor.fetchall()
        
        if participants:
            user_id = random.choice(participants)[0]
            
            cursor.execute(
                "INSERT INTO messages (id, event_id, user_id, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    i,
                    event_id,
                    user_id,
                    f"Message {i} for event {event_id}",
                    int(time.time()) - random.randint(0, 86400)  # Up to 1 day in the past
                )
            )
    
    conn.commit()
    
    # Count the number of records in each table
    cursor.execute("SELECT COUNT(*) FROM users")
    num_users_actual = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM events")
    num_events_actual = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    num_participants = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    num_messages_actual = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"Generated {num_users_actual} users, {num_events_actual} events, {num_participants} participants, and {num_messages_actual} messages")

def main():
    """Main function."""
    logger.info("Initializing test database...")
    
    # Create the database
    create_database()
    
    # Generate test data
    generate_test_data()
    
    logger.info("Test database initialization completed")

if __name__ == "__main__":
    main() 