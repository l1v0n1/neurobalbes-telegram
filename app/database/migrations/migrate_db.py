#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('migration')

def backup_database():
    """Create a backup of the existing database."""
    if os.path.exists("data.db"):
        backup_name = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2("data.db", backup_name)
        logger.info(f"Created database backup: {backup_name}")
        return True
    else:
        logger.warning("No existing database found to backup.")
        return False

def check_old_structure():
    """Check if the database has the old structure."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Check for tables with 'peer' prefix
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'peer%'")
        old_tables = cursor.fetchall()
        
        conn.close()
        
        if old_tables:
            logger.info(f"Found {len(old_tables)} tables with old structure.")
            return True
        else:
            logger.info("No old structure detected.")
            return False
    except Exception as e:
        logger.error(f"Error checking database structure: {e}")
        return False

def migrate_data():
    """Migrate data from old structure to new structure."""
    try:
        # Import the database module
        import database
        
        # Run the migration function
        database.migrate_old_data()
        
        logger.info("Migration completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

def optimize_database():
    """Optimize the database after migration."""
    try:
        import database
        database.optimize_database()
        logger.info("Database optimization completed.")
        return True
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return False

def print_stats():
    """Print database statistics."""
    try:
        import database
        stats = database.get_chat_stats()
        
        logger.info("Database Statistics:")
        logger.info(f"Total chats: {stats['total_chats']}")
        logger.info(f"Total texts: {stats['total_texts']}")
        logger.info(f"Total photos: {stats['total_photos']}")
        logger.info(f"Total stickers: {stats['total_stickers']}")
        logger.info(f"Total blocked stickers: {stats['total_blocked_stickers']}")
        logger.info(f"Database size: {stats['db_size_kb']:.2f} KB")
        
        return True
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return False

def main():
    """Main migration function."""
    logger.info("Starting database migration process...")
    
    # Step 1: Backup the database
    if not backup_database():
        if input("No database backup created. Continue anyway? (y/n): ").lower() != 'y':
            logger.info("Migration aborted by user.")
            return
    
    # Step 2: Check if migration is needed
    if not check_old_structure():
        logger.info("No migration needed. Database already has the new structure.")
        optimize_database()
        print_stats()
        return
    
    # Step 3: Migrate data
    if not migrate_data():
        logger.error("Migration failed. Please restore from backup.")
        return
    
    # Step 4: Optimize database
    optimize_database()
    
    # Step 5: Print statistics
    print_stats()
    
    logger.info("Migration process completed successfully.")
    logger.info("You can now start the bot with the optimized database.")

if __name__ == "__main__":
    main() 