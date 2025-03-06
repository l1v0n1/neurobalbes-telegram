#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import threading
import queue
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_connection_pool')

class DatabaseConnectionPool:
    """
    A connection pool for SQLite database connections.
    
    This class manages a pool of database connections to improve performance
    by reusing connections instead of creating new ones for each operation.
    """
    
    def __init__(self, db_path, min_connections=5, max_connections=20, timeout=5):
        """
        Initialize the connection pool.
        
        Args:
            db_path (str): Path to the SQLite database file
            min_connections (int): Minimum number of connections to keep in the pool
            max_connections (int): Maximum number of connections allowed in the pool
            timeout (int): Timeout in seconds for getting a connection from the pool
        """
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.RLock()
        
        # Initialize the pool with minimum connections
        for _ in range(min_connections):
            self._add_connection()
    
    def _create_connection(self):
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Set journal mode to WAL for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        
        # Set synchronous mode to NORMAL for better performance
        conn.execute("PRAGMA synchronous = NORMAL")
        
        # Increase cache size for better performance
        conn.execute("PRAGMA cache_size = 10000")
        
        # Set temp store to memory for better performance
        conn.execute("PRAGMA temp_store = MEMORY")
        
        return conn
    
    def _add_connection(self):
        """Add a new connection to the pool."""
        with self.lock:
            if self.active_connections < self.max_connections:
                conn = self._create_connection()
                self.pool.put(conn)
                self.active_connections += 1
                logger.debug(f"Added new connection to pool. Active connections: {self.active_connections}")
                return True
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        This is a context manager that will automatically return the connection
        to the pool when the context is exited.
        
        Yields:
            sqlite3.Connection: A database connection
        """
        conn = None
        try:
            # Try to get a connection from the pool
            try:
                conn = self.pool.get(timeout=self.timeout)
                logger.debug("Got connection from pool")
            except queue.Empty:
                # If the pool is empty, try to add a new connection
                if self._add_connection():
                    conn = self.pool.get(timeout=self.timeout)
                    logger.debug("Created new connection as pool was empty")
                else:
                    # If we can't add a new connection, wait for one to become available
                    logger.warning("Connection pool exhausted, waiting for a connection")
                    conn = self.pool.get(timeout=self.timeout * 2)
            
            # Check if the connection is valid
            try:
                conn.execute("SELECT 1")
            except sqlite3.Error:
                # If the connection is invalid, create a new one
                logger.warning("Connection is invalid, creating a new one")
                conn = self._create_connection()
            
            yield conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            # If there was an error, close the connection and create a new one
            if conn:
                try:
                    conn.close()
                    with self.lock:
                        self.active_connections -= 1
                except:
                    pass
                
                # Add a new connection to replace the closed one
                self._add_connection()
            raise
        finally:
            # Return the connection to the pool
            if conn:
                try:
                    # Reset the connection state
                    conn.rollback()
                    self.pool.put(conn)
                    logger.debug("Returned connection to pool")
                except:
                    # If we can't return the connection to the pool, close it
                    try:
                        conn.close()
                        with self.lock:
                            self.active_connections -= 1
                        logger.debug("Closed connection as it couldn't be returned to pool")
                    except:
                        pass
    
    def close_all(self):
        """Close all connections in the pool."""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                    self.active_connections -= 1
                except:
                    pass
            
            logger.info("All connections in the pool have been closed")

# Global connection pool instance
_connection_pool = None

def initialize_pool(db_path="data.db", min_connections=5, max_connections=20):
    """
    Initialize the global connection pool.
    
    Args:
        db_path (str): Path to the SQLite database file
        min_connections (int): Minimum number of connections to keep in the pool
        max_connections (int): Maximum number of connections allowed in the pool
    """
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = DatabaseConnectionPool(
            db_path=db_path,
            min_connections=min_connections,
            max_connections=max_connections
        )
        logger.info(f"Initialized connection pool with {min_connections} connections")
    return _connection_pool

def get_connection_pool():
    """
    Get the global connection pool instance.
    
    Returns:
        DatabaseConnectionPool: The global connection pool instance
    """
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = initialize_pool()
    return _connection_pool

@contextmanager
def get_db_connection():
    """
    Get a database connection from the pool.
    
    This is a convenience function that gets a connection from the global pool.
    
    Yields:
        sqlite3.Connection: A database connection
    """
    pool = get_connection_pool()
    with pool.get_connection() as conn:
        yield conn

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Execute a query using a connection from the pool.
    
    Args:
        query (str): The SQL query to execute
        params (tuple, optional): Parameters for the query
        fetch_one (bool): Whether to fetch one result
        fetch_all (bool): Whether to fetch all results
        commit (bool): Whether to commit the transaction
    
    Returns:
        The query results if fetch_one or fetch_all is True, otherwise None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        start_time = time.time()
        cursor.execute(query, params or ())
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        
        if commit:
            conn.commit()
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        logger.debug(f"Query executed in {execution_time:.2f}ms: {query}")
        
        return result

def close_pool():
    """Close the global connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.close_all()
        _connection_pool = None
        logger.info("Connection pool closed")

# Example usage
if __name__ == "__main__":
    # Initialize the connection pool
    initialize_pool(db_path="data.db", min_connections=3, max_connections=10)
    
    # Execute a query
    result = execute_query("SELECT COUNT(*) FROM users", fetch_one=True)
    print(f"Number of users: {result[0] if result else 0}")
    
    # Close the connection pool
    close_pool() 