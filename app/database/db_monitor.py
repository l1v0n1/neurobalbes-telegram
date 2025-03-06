#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import sqlite3
import logging
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('db_monitor')

def get_db_size():
    """Get the size of the database file in KB."""
    try:
        return os.path.getsize("data.db") / 1024
    except Exception as e:
        logger.error(f"Error getting database size: {e}")
        return 0

def get_table_stats():
    """Get statistics for each table in the database."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting table statistics: {e}")
        return {}

def get_index_stats():
    """Get statistics for each index in the database."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        # Get list of indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return indexes
    except Exception as e:
        logger.error(f"Error getting index statistics: {e}")
        return []

def analyze_query_performance(query, params=(), iterations=10):
    """Analyze the performance of a query."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        times = []
        for _ in range(iterations):
            start_time = time.time()
            cursor.execute(query, params)
            cursor.fetchall()
            end_time = time.time()
            times.append(end_time - start_time)
        
        conn.close()
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        return {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'iterations': iterations
        }
    except Exception as e:
        logger.error(f"Error analyzing query performance: {e}")
        return None

def generate_performance_report():
    """Generate a performance report for common queries."""
    queries = [
        ("Get chat by peer_id", "SELECT * FROM chats WHERE peer_id = ?", ('123456789',)),
        ("Get texts for chat", "SELECT * FROM texts WHERE chat_id = ? LIMIT 100", (1,)),
        ("Get photos for chat", "SELECT * FROM photos WHERE chat_id = ? LIMIT 100", (1,)),
        ("Get stickers for chat", "SELECT * FROM stickers WHERE chat_id = ? LIMIT 100", (1,)),
        ("Count all chats", "SELECT COUNT(*) FROM chats", ()),
        ("Count all texts", "SELECT COUNT(*) FROM texts", ()),
        ("Count all photos", "SELECT COUNT(*) FROM photos", ()),
        ("Count all stickers", "SELECT COUNT(*) FROM stickers", ())
    ]
    
    results = {}
    for name, query, params in queries:
        logger.info(f"Analyzing query: {name}")
        result = analyze_query_performance(query, params)
        if result:
            results[name] = result
    
    return results

def plot_performance_results(results):
    """Plot performance results."""
    try:
        names = list(results.keys())
        avg_times = [results[name]['avg_time'] * 1000 for name in names]  # Convert to ms
        
        plt.figure(figsize=(12, 6))
        plt.bar(names, avg_times)
        plt.xlabel('Query')
        plt.ylabel('Average Time (ms)')
        plt.title('Query Performance')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save the plot
        plt.savefig('query_performance.png')
        logger.info("Performance plot saved to query_performance.png")
    except Exception as e:
        logger.error(f"Error plotting performance results: {e}")

def check_for_optimization_opportunities():
    """Check for optimization opportunities in the database."""
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        opportunities = []
        
        # Check for missing indexes
        cursor.execute("PRAGMA index_list(texts)")
        text_indexes = cursor.fetchall()
        if not text_indexes:
            opportunities.append("Missing indexes on texts table")
        
        # Check for journal mode
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        if journal_mode.lower() != 'wal':
            opportunities.append(f"Journal mode is {journal_mode}, consider using WAL mode")
        
        # Check for synchronous mode
        cursor.execute("PRAGMA synchronous")
        sync_mode = cursor.fetchone()[0]
        if sync_mode > 1:
            opportunities.append(f"Synchronous mode is {sync_mode}, consider using NORMAL (1)")
        
        # Check for cache size
        cursor.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        if cache_size < 10000:
            opportunities.append(f"Cache size is {cache_size}, consider increasing to 10000+")
        
        conn.close()
        return opportunities
    except Exception as e:
        logger.error(f"Error checking for optimization opportunities: {e}")
        return ["Error checking for optimization opportunities"]

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Monitor and analyze database performance')
    parser.add_argument('--report', action='store_true', help='Generate a performance report')
    parser.add_argument('--optimize', action='store_true', help='Check for optimization opportunities')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    args = parser.parse_args()
    
    if not (args.report or args.optimize or args.stats):
        # If no arguments provided, show all
        args.report = args.optimize = args.stats = True
    
    logger.info("Starting database monitor...")
    
    if args.stats:
        # Get database size
        db_size = get_db_size()
        logger.info(f"Database size: {db_size:.2f} KB")
        
        # Get table statistics
        table_stats = get_table_stats()
        logger.info("Table statistics:")
        for table, count in table_stats.items():
            logger.info(f"  {table}: {count} rows")
        
        # Get index statistics
        index_stats = get_index_stats()
        logger.info("Indexes:")
        for index in index_stats:
            logger.info(f"  {index}")
    
    if args.report:
        # Generate performance report
        logger.info("Generating performance report...")
        results = generate_performance_report()
        
        logger.info("Performance results:")
        for name, result in results.items():
            logger.info(f"  {name}:")
            logger.info(f"    Average time: {result['avg_time']*1000:.2f} ms")
            logger.info(f"    Min time: {result['min_time']*1000:.2f} ms")
            logger.info(f"    Max time: {result['max_time']*1000:.2f} ms")
        
        # Plot results
        plot_performance_results(results)
    
    if args.optimize:
        # Check for optimization opportunities
        logger.info("Checking for optimization opportunities...")
        opportunities = check_for_optimization_opportunities()
        
        if opportunities:
            logger.info("Optimization opportunities:")
            for opportunity in opportunities:
                logger.info(f"  - {opportunity}")
        else:
            logger.info("No optimization opportunities found.")
    
    logger.info("Database monitor completed.")

if __name__ == "__main__":
    main() 