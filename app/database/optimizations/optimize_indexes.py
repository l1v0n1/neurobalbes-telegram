#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimize_indexes.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('optimize_indexes')

def get_table_info():
    """Get information about tables in the database."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall() if not table[0].startswith('sqlite_')]
        
        table_info = {}
        for table in tables:
            # Get column information
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            # Get index information
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()
            
            table_info[table] = {
                'columns': columns,
                'indexes': indexes
            }
        
        conn.close()
        return table_info
    except Exception as e:
        logger.error(f"Error getting table information: {e}")
        return None

def create_indexes():
    """Create optimized indexes based on table structure."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Create indexes for users table
        logger.info("Creating indexes for users table...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id)")
        
        # Create indexes for participants table
        logger.info("Creating indexes for participants table...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_user_id ON participants(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_event_id ON participants(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_participants_status ON participants(status)")
        
        # Create indexes for events table
        logger.info("Creating indexes for events table...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_creator_id ON events(creator_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
        
        # Create indexes for messages table
        logger.info("Creating indexes for messages table...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_event_id ON messages(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        
        conn.commit()
        conn.close()
        
        logger.info("Index creation completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False

def benchmark_queries():
    """Benchmark common queries to verify performance improvements."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        queries = [
            ("SELECT * FROM users WHERE username = ?", ("test_user",)),
            ("SELECT * FROM participants WHERE event_id = ?", (1,)),
            ("SELECT * FROM events WHERE date > ? AND status = ?", (time.time(), "active")),
            ("SELECT e.* FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ?", (1,)),
            ("SELECT COUNT(*) FROM participants WHERE event_id = ? AND status = ?", (1, "confirmed"))
        ]
        
        results = {}
        for query, params in queries:
            start_time = time.time()
            cursor.execute(query, params)
            cursor.fetchall()
            end_time = time.time()
            
            results[query] = (end_time - start_time) * 1000  # Convert to milliseconds
        
        conn.close()
        
        logger.info("Query benchmark results (milliseconds):")
        for query, duration in results.items():
            logger.info(f"  {query}: {duration:.2f}ms")
        
        return results
    except Exception as e:
        logger.error(f"Error benchmarking queries: {e}")
        return None

def main():
    """Main function."""
    logger.info("Starting database index optimization...")
    
    # Step 1: Get current table information
    table_info = get_table_info()
    if not table_info:
        logger.error("Failed to get table information. Aborting.")
        return
    
    # Log current table structure
    logger.info("Current database structure:")
    for table, info in table_info.items():
        logger.info(f"  Table: {table}")
        logger.info(f"    Columns: {len(info['columns'])}")
        logger.info(f"    Indexes: {len(info['indexes'])}")
    
    # Step 2: Benchmark queries before optimization
    logger.info("Benchmarking queries before optimization...")
    before_results = benchmark_queries()
    
    # Step 3: Create optimized indexes
    if not create_indexes():
        logger.error("Failed to create indexes. Aborting.")
        return
    
    # Step 4: Benchmark queries after optimization
    logger.info("Benchmarking queries after optimization...")
    after_results = benchmark_queries()
    
    # Step 5: Compare results
    if before_results and after_results:
        logger.info("Performance improvement summary:")
        for query in before_results:
            before = before_results[query]
            after = after_results[query]
            improvement = ((before - after) / before) * 100 if before > 0 else 0
            logger.info(f"  Query: {query}")
            logger.info(f"    Before: {before:.2f}ms")
            logger.info(f"    After: {after:.2f}ms")
            logger.info(f"    Improvement: {improvement:.2f}%")
    
    logger.info("Database index optimization completed.")

if __name__ == "__main__":
    main() 