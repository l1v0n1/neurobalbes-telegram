#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import logging
import time
import json
import os
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimize_queries.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('optimize_queries')

# Common queries that need optimization
COMMON_QUERIES = {
    "get_user": "SELECT * FROM users WHERE username = ?",
    "get_user_by_chat_id": "SELECT * FROM users WHERE chat_id = ?",
    "get_participants": "SELECT * FROM participants WHERE event_id = ?",
    "get_active_events": "SELECT * FROM events WHERE date > ? AND status = 'active'",
    "get_user_events": "SELECT e.* FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ?",
    "count_participants": "SELECT COUNT(*) FROM participants WHERE event_id = ? AND status = ?",
    "get_event_messages": "SELECT * FROM messages WHERE event_id = ? ORDER BY timestamp DESC LIMIT ?",
    "get_user_participation": "SELECT e.*, p.status FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ? ORDER BY e.date DESC",
    "search_events": "SELECT * FROM events WHERE title LIKE ? OR description LIKE ?",
    "get_recent_events": "SELECT * FROM events ORDER BY date DESC LIMIT ?"
}

# Optimized versions of the common queries
OPTIMIZED_QUERIES = {
    "get_user": "SELECT id, username, chat_id, created_at FROM users WHERE username = ?",
    "get_user_by_chat_id": "SELECT id, username, chat_id, created_at FROM users WHERE chat_id = ?",
    "get_participants": "SELECT user_id, status FROM participants WHERE event_id = ?",
    "get_active_events": "SELECT id, title, date, status FROM events WHERE date > ? AND status = 'active' LIMIT 100",
    "get_user_events": "SELECT e.id, e.title, e.date, e.status FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ? ORDER BY e.date DESC LIMIT 50",
    "count_participants": "SELECT COUNT(*) FROM participants WHERE event_id = ? AND status = ?",
    "get_event_messages": "SELECT id, user_id, content, timestamp FROM messages WHERE event_id = ? ORDER BY timestamp DESC LIMIT ?",
    "get_user_participation": "SELECT e.id, e.title, e.date, e.status, p.status as participation_status FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ? ORDER BY e.date DESC LIMIT 50",
    "search_events": "SELECT id, title, date, status FROM events WHERE title LIKE ? OR description LIKE ? LIMIT 50",
    "get_recent_events": "SELECT id, title, date, status FROM events ORDER BY date DESC LIMIT ?"
}

@contextmanager
def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect("data.db")
    try:
        yield conn
    finally:
        conn.close()

def benchmark_query(conn, query, params, iterations=10):
    """Benchmark a query by running it multiple times and measuring the average execution time."""
    cursor = conn.cursor()
    total_time = 0
    
    for _ in range(iterations):
        start_time = time.time()
        cursor.execute(query, params)
        cursor.fetchall()
        end_time = time.time()
        total_time += (end_time - start_time)
    
    avg_time = (total_time / iterations) * 1000  # Convert to milliseconds
    return avg_time

def analyze_query_plans():
    """Analyze the query plans for common queries and their optimized versions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        results = {}
        
        for query_name, query in COMMON_QUERIES.items():
            # Get sample parameters for the query
            params = get_sample_params(query_name)
            
            # Get the query plan for the original query
            cursor.execute(f"EXPLAIN QUERY PLAN {query}", params)
            original_plan = cursor.fetchall()
            
            # Get the query plan for the optimized query
            optimized_query = OPTIMIZED_QUERIES.get(query_name, query)
            cursor.execute(f"EXPLAIN QUERY PLAN {optimized_query}", params)
            optimized_plan = cursor.fetchall()
            
            # Benchmark the original query
            original_time = benchmark_query(conn, query, params)
            
            # Benchmark the optimized query
            optimized_time = benchmark_query(conn, optimized_query, params)
            
            # Calculate improvement
            improvement = ((original_time - optimized_time) / original_time) * 100 if original_time > 0 else 0
            
            results[query_name] = {
                "original_query": query,
                "optimized_query": optimized_query,
                "original_plan": original_plan,
                "optimized_plan": optimized_plan,
                "original_time": original_time,
                "optimized_time": optimized_time,
                "improvement": improvement
            }
            
            logger.info(f"Query: {query_name}")
            logger.info(f"  Original: {original_time:.2f}ms")
            logger.info(f"  Optimized: {optimized_time:.2f}ms")
            logger.info(f"  Improvement: {improvement:.2f}%")
        
        return results

def get_sample_params(query_name):
    """Get sample parameters for a query."""
    if query_name == "get_user":
        return ("test_user",)
    elif query_name == "get_user_by_chat_id":
        return (123456,)
    elif query_name == "get_participants":
        return (1,)
    elif query_name == "get_active_events":
        return (time.time(),)
    elif query_name == "get_user_events":
        return (1,)
    elif query_name == "count_participants":
        return (1, "confirmed")
    elif query_name == "get_event_messages":
        return (1, 10)
    elif query_name == "get_user_participation":
        return (1,)
    elif query_name == "search_events":
        return ("%party%", "%party%")
    elif query_name == "get_recent_events":
        return (10,)
    else:
        return ()

def create_query_views():
    """Create views for optimized queries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create view for active events
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS active_events AS
        SELECT id, title, creator_id, date, location, description, status
        FROM events
        WHERE status = 'active' AND date > strftime('%s', 'now')
        """)
        
        # Create view for user participation
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS user_participation AS
        SELECT 
            e.id as event_id, 
            e.title as event_title, 
            e.date as event_date, 
            e.status as event_status,
            p.user_id,
            p.status as participation_status
        FROM events e
        JOIN participants p ON e.id = p.event_id
        """)
        
        # Create view for event statistics
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS event_stats AS
        SELECT 
            e.id as event_id,
            e.title as event_title,
            COUNT(p.id) as total_participants,
            SUM(CASE WHEN p.status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_participants,
            SUM(CASE WHEN p.status = 'pending' THEN 1 ELSE 0 END) as pending_participants,
            SUM(CASE WHEN p.status = 'declined' THEN 1 ELSE 0 END) as declined_participants
        FROM events e
        LEFT JOIN participants p ON e.id = p.event_id
        GROUP BY e.id
        """)
        
        conn.commit()
        logger.info("Created database views for optimized queries")

def generate_query_recommendations():
    """Generate recommendations for query optimization."""
    results = analyze_query_plans()
    
    recommendations = []
    
    for query_name, result in results.items():
        if result["improvement"] < 10:
            # If the improvement is less than 10%, suggest further optimization
            recommendations.append({
                "query_name": query_name,
                "original_query": result["original_query"],
                "optimized_query": result["optimized_query"],
                "improvement": result["improvement"],
                "recommendation": "Consider further optimization or adding indexes"
            })
        elif result["improvement"] >= 50:
            # If the improvement is significant, recommend using the optimized query
            recommendations.append({
                "query_name": query_name,
                "original_query": result["original_query"],
                "optimized_query": result["optimized_query"],
                "improvement": result["improvement"],
                "recommendation": "Use the optimized query for significant performance improvement"
            })
    
    # Save recommendations to a file
    with open("query_recommendations.json", "w") as f:
        json.dump(recommendations, f, indent=2)
    
    logger.info(f"Generated {len(recommendations)} query optimization recommendations")
    return recommendations

def main():
    """Main function."""
    logger.info("Starting query optimization process...")
    
    # Step 1: Create optimized query views
    create_query_views()
    
    # Step 2: Analyze query plans and benchmark queries
    analyze_query_plans()
    
    # Step 3: Generate query optimization recommendations
    recommendations = generate_query_recommendations()
    
    # Print recommendations
    logger.info("Query optimization recommendations:")
    for rec in recommendations:
        logger.info(f"  Query: {rec['query_name']}")
        logger.info(f"    Improvement: {rec['improvement']:.2f}%")
        logger.info(f"    Recommendation: {rec['recommendation']}")
    
    logger.info("Query optimization process completed.")

if __name__ == "__main__":
    main() 