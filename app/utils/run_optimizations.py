#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import subprocess
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimization_run.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('run_optimizations')

def run_script(script_name, description):
    """Run a Python script and log the output."""
    logger.info(f"Running {description}...")
    
    start_time = time.time()
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Log the output
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"{description} completed successfully in {duration:.2f} seconds")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {description}: {e}")
        
        # Log the error output
        for line in e.stderr.splitlines():
            logger.error(f"  {line}")
        
        return False

def backup_database():
    """Create a backup of the database before optimization."""
    if not os.path.exists("data.db"):
        logger.warning("No database file found to backup")
        return True
    
    backup_name = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        import shutil
        shutil.copy2("data.db", backup_name)
        logger.info(f"Created database backup: {backup_name}")
        return True
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        return False

def main():
    """Main function to run all optimizations."""
    logger.info("Starting database optimization process...")
    
    # Step 1: Backup the database
    if not backup_database():
        if input("Failed to create database backup. Continue anyway? (y/n): ").lower() != 'y':
            logger.info("Optimization aborted by user")
            return
    
    # Step 2: Run database structure optimization
    if not run_script("optimize_db.py", "database structure optimization"):
        if input("Database structure optimization failed. Continue with other optimizations? (y/n): ").lower() != 'y':
            logger.info("Optimization process aborted by user")
            return
    
    # Step 3: Run index optimization
    if not run_script("optimize_indexes.py", "index optimization"):
        if input("Index optimization failed. Continue with other optimizations? (y/n): ").lower() != 'y':
            logger.info("Optimization process aborted by user")
            return
    
    # Step 4: Run query optimization
    if not run_script("optimize_queries.py", "query optimization"):
        if input("Query optimization failed. Continue with other optimizations? (y/n): ").lower() != 'y':
            logger.info("Optimization process aborted by user")
            return
    
    # Step 5: Run batch processing benchmark
    run_script("batch_processor.py", "batch processing benchmark")
    
    logger.info("Database optimization process completed")
    
    # Print summary
    logger.info("Optimization Summary:")
    logger.info("1. Database structure has been optimized for better performance")
    logger.info("2. Indexes have been created to speed up common queries")
    logger.info("3. Query optimizations have been applied")
    logger.info("4. Batch processing has been implemented for handling large numbers of participants")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Review the log files for detailed information about each optimization")
    logger.info("2. Test the application with a large number of users and events")
    logger.info("3. Monitor database performance and make further optimizations if needed")

if __name__ == "__main__":
    main() 