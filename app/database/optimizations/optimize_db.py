#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import os
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimize_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('optimize_db')

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

def optimize_database():
    """Apply optimizations to the database."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Set journal mode to WAL for better concurrency
        cursor.execute("PRAGMA journal_mode = WAL")
        journal_mode = cursor.fetchone()[0]
        logger.info(f"Journal mode set to: {journal_mode}")
        
        # Set synchronous mode to NORMAL for better performance
        cursor.execute("PRAGMA synchronous = NORMAL")
        logger.info("Synchronous mode set to NORMAL")
        
        # Increase cache size for better performance
        cursor.execute("PRAGMA cache_size = 10000")
        logger.info("Cache size increased to 10000")
        
        # Set temp store to memory for better performance
        cursor.execute("PRAGMA temp_store = MEMORY")
        logger.info("Temp store set to MEMORY")
        
        # Run VACUUM to defragment the database
        logger.info("Running VACUUM to defragment the database...")
        cursor.execute("VACUUM")
        
        # Run ANALYZE to update statistics
        logger.info("Running ANALYZE to update statistics...")
        cursor.execute("ANALYZE")
        
        conn.commit()
        conn.close()
        
        logger.info("Database optimization completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return False

def verify_optimizations():
    """Verify that the optimizations were applied correctly."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Check journal mode
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        
        # Check synchronous mode
        cursor.execute("PRAGMA synchronous")
        sync_mode = cursor.fetchone()[0]
        
        # Check cache size
        cursor.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        
        # Check temp store
        cursor.execute("PRAGMA temp_store")
        temp_store = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info("Current database settings:")
        logger.info(f"  Journal mode: {journal_mode}")
        logger.info(f"  Synchronous mode: {sync_mode}")
        logger.info(f"  Cache size: {cache_size}")
        logger.info(f"  Temp store: {temp_store}")
        
        return True
    except Exception as e:
        logger.error(f"Error verifying optimizations: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting database optimization process...")
    
    # Step 1: Backup the database
    if not backup_database():
        if input("No database backup created. Continue anyway? (y/n): ").lower() != 'y':
            logger.info("Optimization aborted by user.")
            return
    
    # Step 2: Apply optimizations
    if optimize_database():
        # Step 3: Verify optimizations
        verify_optimizations()
        
        logger.info("Database optimization process completed successfully.")
    else:
        logger.error("Database optimization failed.")

if __name__ == "__main__":
    main() 