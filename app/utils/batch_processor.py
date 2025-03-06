#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import time
import json
import os
import threading
import queue
from contextlib import contextmanager
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('batch_processor')

# Import the connection pool if available
try:
    from db_connection_pool import get_db_connection, execute_query
    USE_CONNECTION_POOL = True
    logger.info("Using connection pool for database operations")
except ImportError:
    USE_CONNECTION_POOL = False
    logger.warning("Connection pool not available, using direct connections")
    
    @contextmanager
    def get_db_connection():
        """Get a database connection."""
        conn = sqlite3.connect("data.db")
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
        """Execute a query using a direct connection."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            
            if commit:
                conn.commit()
            
            return result

class BatchProcessor:
    """
    A batch processor for handling large numbers of database operations.
    
    This class provides methods for efficiently processing large numbers of
    database operations in batches, reducing the overhead of individual
    transactions and improving overall performance.
    """
    
    def __init__(self, batch_size=100, max_queue_size=1000, num_workers=4):
        """
        Initialize the batch processor.
        
        Args:
            batch_size (int): Number of operations to process in a single batch
            max_queue_size (int): Maximum size of the operation queue
            num_workers (int): Number of worker threads to process batches
        """
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.workers = []
        self.running = False
        self.stats = {
            "operations_queued": 0,
            "operations_processed": 0,
            "batches_processed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def start(self):
        """Start the batch processor workers."""
        if self.running:
            logger.warning("Batch processor is already running")
            return
        
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.num_workers} batch processor workers")
    
    def stop(self):
        """Stop the batch processor workers."""
        if not self.running:
            logger.warning("Batch processor is not running")
            return
        
        self.running = False
        
        # Wait for all workers to finish
        for worker in self.workers:
            worker.join()
        
        self.workers = []
        self.stats["end_time"] = datetime.now()
        
        # Calculate processing time
        if self.stats["start_time"] and self.stats["end_time"]:
            processing_time = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            operations_per_second = self.stats["operations_processed"] / processing_time if processing_time > 0 else 0
            
            logger.info(f"Batch processor stopped after {processing_time:.2f} seconds")
            logger.info(f"Processed {self.stats['operations_processed']} operations in {self.stats['batches_processed']} batches")
            logger.info(f"Processing rate: {operations_per_second:.2f} operations per second")
            logger.info(f"Errors: {self.stats['errors']}")
    
    def _worker(self, worker_id):
        """Worker thread function."""
        logger.debug(f"Worker {worker_id} started")
        
        batch = []
        last_batch_time = time.time()
        
        while self.running or not self.queue.empty():
            try:
                # Get an operation from the queue with a timeout
                try:
                    operation = self.queue.get(timeout=1.0)
                    batch.append(operation)
                    self.queue.task_done()
                except queue.Empty:
                    # If the queue is empty, process any remaining operations in the batch
                    if batch and (time.time() - last_batch_time > 5.0 or not self.running):
                        self._process_batch(batch)
                        batch = []
                        last_batch_time = time.time()
                    continue
                
                # If the batch is full, process it
                if len(batch) >= self.batch_size:
                    self._process_batch(batch)
                    batch = []
                    last_batch_time = time.time()
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
                self.stats["errors"] += 1
        
        # Process any remaining operations in the batch
        if batch:
            self._process_batch(batch)
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def _process_batch(self, batch):
        """Process a batch of operations."""
        if not batch:
            return
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Group operations by type
                inserts = {}
                updates = {}
                deletes = {}
                
                for operation in batch:
                    op_type = operation["type"]
                    table = operation["table"]
                    
                    if op_type == "insert":
                        if table not in inserts:
                            inserts[table] = []
                        inserts[table].append(operation)
                    elif op_type == "update":
                        if table not in updates:
                            updates[table] = []
                        updates[table].append(operation)
                    elif op_type == "delete":
                        if table not in deletes:
                            deletes[table] = []
                        deletes[table].append(operation)
                
                # Process inserts
                for table, operations in inserts.items():
                    if not operations:
                        continue
                    
                    # Get column names from the first operation
                    columns = operations[0]["data"].keys()
                    placeholders = ", ".join(["?"] * len(columns))
                    column_str = ", ".join(columns)
                    
                    # Prepare the query
                    query = f"INSERT OR IGNORE INTO {table} ({column_str}) VALUES ({placeholders})"
                    
                    # Execute the query for each operation
                    for operation in operations:
                        try:
                            values = tuple(operation["data"].get(col) for col in columns)
                            cursor.execute(query, values)
                            if cursor.rowcount > 0:
                                self.stats["operations_processed"] += 1
                        except Exception as e:
                            logger.error(f"Error executing insert: {e}")
                            self.stats["errors"] += 1
                
                # Process updates
                for table, operations in updates.items():
                    for operation in operations:
                        try:
                            # Prepare the SET clause
                            set_clause = ", ".join([f"{col} = ?" for col in operation["data"].keys()])
                            
                            # Prepare the WHERE clause
                            where_clause = " AND ".join([f"{col} = ?" for col in operation["where"].keys()])
                            
                            # Prepare the query
                            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
                            
                            # Prepare the values
                            values = tuple(list(operation["data"].values()) + list(operation["where"].values()))
                            
                            # Execute the query
                            cursor.execute(query, values)
                            if cursor.rowcount > 0:
                                self.stats["operations_processed"] += 1
                        except Exception as e:
                            logger.error(f"Error executing update: {e}")
                            self.stats["errors"] += 1
                
                # Process deletes
                for table, operations in deletes.items():
                    for operation in operations:
                        try:
                            # Prepare the WHERE clause
                            where_clause = " AND ".join([f"{col} = ?" for col in operation["where"].keys()])
                            
                            # Prepare the query
                            query = f"DELETE FROM {table} WHERE {where_clause}"
                            
                            # Prepare the values
                            values = tuple(operation["where"].values())
                            
                            # Execute the query
                            cursor.execute(query, values)
                            if cursor.rowcount > 0:
                                self.stats["operations_processed"] += 1
                        except Exception as e:
                            logger.error(f"Error executing delete: {e}")
                            self.stats["errors"] += 1
                
                # Commit the transaction
                conn.commit()
                
                # Update stats
                self.stats["batches_processed"] += 1
                
                logger.debug(f"Processed batch of {len(batch)} operations")
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            self.stats["errors"] += 1
    
    def queue_operation(self, operation):
        """
        Queue an operation for batch processing.
        
        Args:
            operation (dict): The operation to queue
                {
                    "type": "insert" | "update" | "delete",
                    "table": "table_name",
                    "data": {"column1": value1, "column2": value2, ...},  # For insert and update
                    "where": {"column1": value1, "column2": value2, ...}  # For update and delete
                }
        
        Returns:
            bool: True if the operation was queued successfully, False otherwise
        """
        if not self.running:
            logger.warning("Cannot queue operation: batch processor is not running")
            return False
        
        try:
            self.queue.put(operation, timeout=1.0)
            self.stats["operations_queued"] += 1
            return True
        except queue.Full:
            logger.warning("Operation queue is full")
            return False
    
    def wait_until_done(self):
        """Wait until all queued operations have been processed."""
        self.queue.join()

def add_participants_batch(event_id, participants, batch_size=100):
    """
    Add multiple participants to an event using batch processing.
    
    Args:
        event_id (int): The ID of the event
        participants (list): List of participant data
            [{"user_id": user_id, "status": status}, ...]
        batch_size (int): Number of participants to process in a single batch
    
    Returns:
        int: Number of participants added
    """
    processor = BatchProcessor(batch_size=batch_size)
    processor.start()
    
    count = 0
    for participant in participants:
        operation = {
            "type": "insert",
            "table": "participants",
            "data": {
                "event_id": event_id,
                "user_id": participant["user_id"],
                "status": participant["status"],
                "joined_at": int(time.time())
            }
        }
        
        if processor.queue_operation(operation):
            count += 1
    
    processor.wait_until_done()
    processor.stop()
    
    # Return the actual number of operations processed, not the number queued
    return processor.stats["operations_processed"]

def update_participants_batch(event_id, status_updates, batch_size=100):
    """
    Update the status of multiple participants using batch processing.
    
    Args:
        event_id (int): The ID of the event
        status_updates (list): List of status updates
            [{"user_id": user_id, "status": new_status}, ...]
        batch_size (int): Number of updates to process in a single batch
    
    Returns:
        int: Number of participants updated
    """
    processor = BatchProcessor(batch_size=batch_size)
    processor.start()
    
    count = 0
    for update in status_updates:
        operation = {
            "type": "update",
            "table": "participants",
            "data": {
                "status": update["status"],
                "updated_at": int(time.time())
            },
            "where": {
                "event_id": event_id,
                "user_id": update["user_id"]
            }
        }
        
        if processor.queue_operation(operation):
            count += 1
    
    processor.wait_until_done()
    processor.stop()
    
    return count

def remove_participants_batch(event_id, user_ids, batch_size=100):
    """
    Remove multiple participants from an event using batch processing.
    
    Args:
        event_id (int): The ID of the event
        user_ids (list): List of user IDs to remove
        batch_size (int): Number of removals to process in a single batch
    
    Returns:
        int: Number of participants removed
    """
    processor = BatchProcessor(batch_size=batch_size)
    processor.start()
    
    count = 0
    for user_id in user_ids:
        operation = {
            "type": "delete",
            "table": "participants",
            "where": {
                "event_id": event_id,
                "user_id": user_id
            }
        }
        
        if processor.queue_operation(operation):
            count += 1
    
    processor.wait_until_done()
    processor.stop()
    
    return count

def generate_test_data(num_users=1000, num_events=50, max_participants_per_event=200):
    """
    Generate test data for benchmarking.
    
    Args:
        num_users (int): Number of users to generate
        num_events (int): Number of events to generate
        max_participants_per_event (int): Maximum number of participants per event
    
    Returns:
        dict: Generated test data
    """
    import random
    
    # Generate users
    users = []
    for i in range(1, num_users + 1):
        users.append({
            "id": i,
            "username": f"user_{i}",
            "chat_id": 1000000 + i,
            "created_at": int(time.time())
        })
    
    # Generate events
    events = []
    for i in range(1, num_events + 1):
        creator_id = random.randint(1, num_users)
        events.append({
            "id": i,
            "title": f"Event {i}",
            "creator_id": creator_id,
            "date": int(time.time()) + random.randint(86400, 2592000),  # 1-30 days in the future
            "location": f"Location {i}",
            "description": f"Description for event {i}",
            "status": random.choice(["active", "cancelled", "completed"])
        })
    
    # Generate participants
    participants = []
    for event in events:
        num_participants = random.randint(10, max_participants_per_event)
        event_participants = random.sample(range(1, num_users + 1), num_participants)
        
        for user_id in event_participants:
            participants.append({
                "event_id": event["id"],
                "user_id": user_id,
                "status": random.choice(["confirmed", "pending", "declined"]),
                "joined_at": int(time.time())
            })
    
    return {
        "users": users,
        "events": events,
        "participants": participants
    }

def benchmark_batch_processing():
    """
    Benchmark batch processing performance.
    
    This function generates test data and measures the performance of
    batch processing operations compared to individual operations.
    """
    logger.info("Generating test data...")
    test_data = generate_test_data()
    
    logger.info(f"Generated {len(test_data['users'])} users, {len(test_data['events'])} events, and {len(test_data['participants'])} participants")
    
    # Create a new event for testing
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create a new event
        event_id = 9999
        creator_id = 1
        cursor.execute(
            "INSERT INTO events (id, title, creator_id, date, location, description, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                "Test Event",
                creator_id,
                int(time.time()) + 86400,  # 1 day in the future
                "Test Location",
                "Test Description",
                "active"
            )
        )
        conn.commit()
    
    # Benchmark adding participants
    # Use a different set of users for each test to avoid unique constraint violations
    participants = [{"user_id": user["id"], "status": "pending"} for user in test_data["users"][:500]]
    
    logger.info(f"Benchmarking adding {len(participants)} participants...")
    
    # Measure time for individual inserts
    start_time = time.time()
    count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for participant in participants[:100]:  # Only test with a subset for individual inserts
            try:
                cursor.execute(
                    "INSERT INTO participants (event_id, user_id, status, joined_at) VALUES (?, ?, ?, ?)",
                    (event_id, participant["user_id"], participant["status"], int(time.time()))
                )
                count += 1
            except sqlite3.IntegrityError:
                # Skip if the participant already exists
                pass
        conn.commit()
    individual_time = time.time() - start_time
    
    logger.info(f"Added {count} participants individually in {individual_time:.2f} seconds ({count / individual_time:.2f} per second)")
    
    # Measure time for batch inserts
    # Use a different event ID to avoid unique constraint violations
    event_id = 10000
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (id, title, creator_id, date, location, description, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                "Test Event 2",
                creator_id,
                int(time.time()) + 86400,  # 1 day in the future
                "Test Location 2",
                "Test Description 2",
                "active"
            )
        )
        conn.commit()
    
    start_time = time.time()
    count = add_participants_batch(event_id, participants, batch_size=100)
    batch_time = time.time() - start_time
    
    logger.info(f"Added {count} participants in batches in {batch_time:.2f} seconds ({count / batch_time:.2f} per second)")
    
    # Calculate speedup
    if individual_time > 0 and count > 0:
        individual_rate = 100 / individual_time  # Operations per second for individual inserts
        batch_rate = count / batch_time if batch_time > 0 else 0  # Operations per second for batch inserts
        speedup = batch_rate / individual_rate if individual_rate > 0 else 0
        
        logger.info(f"Batch processing speedup: {speedup:.2f}x")
    
    # Benchmark updating participants
    status_updates = [{"user_id": user["id"], "status": "confirmed"} for user in test_data["users"][:250]]
    
    logger.info(f"Benchmarking updating {len(status_updates)} participants...")
    
    # Measure time for batch updates
    start_time = time.time()
    count = update_participants_batch(event_id, status_updates, batch_size=100)
    update_time = time.time() - start_time
    
    logger.info(f"Updated {count} participants in batches in {update_time:.2f} seconds ({count / update_time:.2f} per second)")
    
    # Benchmark removing participants
    user_ids = [user["id"] for user in test_data["users"][:250]]
    
    logger.info(f"Benchmarking removing {len(user_ids)} participants...")
    
    # Measure time for batch deletes
    start_time = time.time()
    count = remove_participants_batch(event_id, user_ids, batch_size=100)
    delete_time = time.time() - start_time
    
    logger.info(f"Removed {count} participants in batches in {delete_time:.2f} seconds ({count / delete_time:.2f} per second)")

def main():
    """Main function."""
    logger.info("Starting batch processor benchmark...")
    
    # Create tables if they don't exist
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            chat_id INTEGER UNIQUE,
            created_at INTEGER
        )
        """)
        
        # Create events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
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
        CREATE TABLE IF NOT EXISTS participants (
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
        
        conn.commit()
    
    # Run the benchmark
    benchmark_batch_processing()
    
    logger.info("Batch processor benchmark completed.")

if __name__ == "__main__":
    main() 