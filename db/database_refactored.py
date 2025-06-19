"""
ISTQB AI Certification Portal - Database Module (Refactored)

This module provides a DRY, modular implementation of the database functionality for the ISTQB AI Portal.
It implements the Data Access Object (DAO) pattern to organize database operations by entity.

Key improvements over the original implementation:
1. Separation of concerns using DAO classes for different entities
2. Generic CRUD operations through BaseDAO
3. Transaction management with decorators
4. Better error handling and logging
5. Clear schema definition and management
6. Migration support for database evolution

Backward compatibility:
This module maintains backwards compatibility with the original database.py interface.
Applications can switch to using this module without code changes.
"""

import os
import sqlite3
from pathlib import Path
import functools
from typing import Any, Dict, List, Tuple, Union, Optional, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define database directory and file path
DB_DIR = Path(__file__).parent
DB_FILE = DB_DIR / "istqb_portal.db"

# Database schema definitions
SCHEMA = {
    "users": '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    "user_progress": '''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            completion_date TIMESTAMP,
            notes TEXT,
            UNIQUE(user_id, chapter_id, topic_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''',
    "user_notes": '''
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''',
    "study_sessions": '''
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''',
    "quiz_results": '''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            topics TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    '''
}

# Database Migration Definitions
MIGRATIONS = [
    {
        "check": "SELECT name FROM sqlite_master WHERE type='table' AND name='users'",
        "check_field": "PRAGMA table_info(users)",
        "field_name": "is_admin",
        "migration": "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
        "message": "Migrating users table to add is_admin column..."
    }
]

def ensure_db_exists() -> str:
    """Ensure the database directory exists and return the database path."""
    os.makedirs(DB_DIR, exist_ok=True)
    return str(DB_FILE)

def get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    db_path = ensure_db_exists()
    conn = sqlite3.connect(db_path)
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def db_transaction(func):
    """Decorator for functions that need database transactions.
    Handles connection, commit/rollback, and closing."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if the first argument is already a connection
        if args and isinstance(args[0], sqlite3.Connection):
            # Connection provided, use it
            return func(*args, **kwargs)
        else:
            # No connection provided, create one
            conn = get_connection()
            try:
                result = func(conn, *args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error in {func.__name__}: {str(e)}")
                return False if "return_status" not in kwargs else (False, str(e))
            finally:
                conn.close()
    return wrapper

def db_query(func):
    """Decorator for query functions that don't modify the database."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if the first argument is already a connection
        if args and isinstance(args[0], sqlite3.Connection):
            # Connection provided, use it
            return func(*args, **kwargs)
        else:
            # No connection provided, create one
            conn = get_connection()
            try:
                result = func(conn, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Database query error in {func.__name__}: {str(e)}")
                return None
            finally:
                conn.close()
    return wrapper

def execute_query(conn, query, params=None):
    """Execute a query with parameters and return the cursor."""
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    return cursor

def run_migrations(conn):
    """Run all pending database migrations."""
    need_migration = False
    cursor = conn.cursor()
    
    for migration in MIGRATIONS:
        # Check if the table exists
        cursor.execute(migration["check"])
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if the field exists
            cursor.execute(migration["check_field"])
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if migration["field_name"] not in column_names:
                logger.info(migration["message"])
                cursor.execute(migration["migration"])
                need_migration = True
    
    return need_migration

def initialize_database():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Run migrations
    need_migration = run_migrations(conn)
    
    # Create all tables defined in the schema
    for table_name, table_schema in SCHEMA.items():
        cursor.execute(table_schema)
    
    # Create default admin user
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        cursor.execute(
            "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
            ("admin", "admin@example.com", 1)
        )
        logger.info("Created default admin user. Username: admin")
    elif need_migration:
        # Update existing admin user during migration
        cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
        logger.info("Updated admin user with admin privileges")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully.")

# Generic CRUD operations
class BaseDAO:
    """Data Access Object base class with CRUD operations"""
    
    @staticmethod
    @db_transaction
    def insert(conn, table, data):
        """Generic insert function for any table."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data.keys()])
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = execute_query(conn, query, values)
        return cursor.lastrowid
    
    @staticmethod
    @db_query
    def select_by_id(conn, table, id_value, id_field='id'):
        """Generic select by ID function."""
        query = f"SELECT * FROM {table} WHERE {id_field} = ?"
        cursor = execute_query(conn, query, (id_value,))
        return cursor.fetchone()
    
    @staticmethod
    @db_query
    def select_all(conn, table, condition=None, params=None, order_by=None):
        """Generic select all function with optional condition."""
        query = f"SELECT * FROM {table}"
        if condition:
            query += f" WHERE {condition}"
        if order_by:
            query += f" ORDER BY {order_by}"
        
        cursor = execute_query(conn, query, params)
        return cursor.fetchall()
    
    @staticmethod
    @db_transaction
    def update(conn, table, id_value, data, id_field='id'):
        """Generic update function."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [id_value]
        
        query = f"UPDATE {table} SET {set_clause} WHERE {id_field} = ?"
        execute_query(conn, query, values)
        return True
    
    @staticmethod
    @db_transaction
    def delete(conn, table, id_value, id_field='id'):
        """Generic delete function."""
        query = f"DELETE FROM {table} WHERE {id_field} = ?"
        execute_query(conn, query, (id_value,))
        return True
    
    @staticmethod
    @db_query
    def count(conn, table, condition=None, params=None):
        """Generic count function."""
        query = f"SELECT COUNT(*) FROM {table}"
        if condition:
            query += f" WHERE {condition}"
        
        cursor = execute_query(conn, query, params)
        return cursor.fetchone()[0]


# User Management
class UserDAO:
    """Data Access Object for user-related operations."""
    
    @staticmethod
    @db_transaction
    def get_or_create(conn, username, email=None, is_admin=False):
        """Get a user by username or create if not exists."""
        cursor = execute_query(conn, "SELECT id, is_admin FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            user_id = user[0]
            
            # Update admin status if needed
            if is_admin and not user[1]:
                execute_query(conn, "UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        else:
            # Create new user
            cursor = execute_query(
                conn,
                "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
                (username, email, 1 if is_admin else 0)
            )
            user_id = cursor.lastrowid
        
        return user_id
    
    @staticmethod
    @db_query
    def is_admin(conn, username):
        """Check if a user has admin privileges."""
        cursor = execute_query(conn, "SELECT is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return True
        return False
    
    @staticmethod
    @db_transaction
    def set_admin_status(conn, username, is_admin_status):
        """Grant or revoke admin privileges for a user."""
        execute_query(
            conn, 
            "UPDATE users SET is_admin = ? WHERE username = ?", 
            (1 if is_admin_status else 0, username)
        )
        return True
    
    @staticmethod
    @db_query
    def get_all(conn):
        """Get all registered users for admin view."""
        cursor = execute_query(conn, """
            SELECT 
                id, 
                username, 
                email, 
                is_admin, 
                created_at,
                (SELECT COUNT(*) FROM user_progress WHERE user_id = users.id) as progress_count,
                (SELECT COUNT(*) FROM user_notes WHERE user_id = users.id) as notes_count,
                (SELECT COUNT(*) FROM study_sessions WHERE user_id = users.id) as sessions_count,
                (SELECT COUNT(*) FROM quiz_results WHERE user_id = users.id) as quiz_count
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "username": row[1],
                "email": row[2] or "N/A",
                "is_admin": bool(row[3]),
                "created_at": row[4],
                "progress_items": row[5],
                "notes_count": row[6],
                "study_sessions": row[7],
                "quiz_attempts": row[8]
            })
        
        return users
    
    @staticmethod
    @db_query
    def get_details(conn, user_id):
        """Get detailed information about a specific user."""
        # Get user basic info
        cursor = execute_query(
            conn, 
            "SELECT id, username, email, is_admin, created_at FROM users WHERE id = ?", 
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            return None
        
        user_data = {
            "id": user[0],
            "username": user[1],
            "email": user[2] or "N/A",
            "is_admin": bool(user[3]),
            "created_at": user[4],
        }
        
        # Get progress statistics
        cursor = execute_query(conn, """
            SELECT 
                COUNT(*) as total_topics,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_topics
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,))
        
        progress = cursor.fetchone()
        if progress:
            total_topics = progress[0] or 0
            completed_topics = progress[1] or 0
            completion_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            
            user_data["progress"] = {
                "total_topics": total_topics,
                "completed_topics": completed_topics,
                "completion_percentage": completion_percentage
            }
        
        # Get quiz statistics
        cursor = execute_query(conn, """
            SELECT 
                COUNT(*) as attempts,
                AVG(correct_answers * 100.0 / total_questions) as avg_score
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))
        
        quiz_stats = cursor.fetchone()
        if quiz_stats:
            user_data["quiz_stats"] = {
                "attempts": quiz_stats[0],
                "avg_score": quiz_stats[1] or 0
            }
        
        # Get study time statistics
        cursor = execute_query(conn, """
            SELECT 
                COUNT(*) as sessions,
                SUM(duration_minutes) as total_minutes
            FROM study_sessions
            WHERE user_id = ?
        """, (user_id,))
        
        study_stats = cursor.fetchone()
        if study_stats:
            user_data["study_stats"] = {
                "sessions": study_stats[0],
                "total_minutes": study_stats[1] or 0
            }
        
        return user_data
    
    @staticmethod
    @db_transaction
    def delete(conn, user_id, admin_user_id):
        """Delete a user and all their data (admin only)."""
        # Don't allow deleting yourself
        if user_id == admin_user_id:
            return False, "Cannot delete your own account"
        
        # Start a transaction (handled by decorator)
        execute_query(conn, "DELETE FROM user_progress WHERE user_id = ?", (user_id,))
        execute_query(conn, "DELETE FROM user_notes WHERE user_id = ?", (user_id,))
        execute_query(conn, "DELETE FROM study_sessions WHERE user_id = ?", (user_id,))
        execute_query(conn, "DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
        execute_query(conn, "DELETE FROM users WHERE id = ?", (user_id,))
        
        return True, f"User ID {user_id} and all associated data successfully deleted"
    
    @staticmethod
    @db_transaction
    def update_metadata(conn, user_id, email=None, is_admin=None):
        """Update user metadata (admin function)."""
        updates = []
        params = []
        
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        
        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(1 if is_admin else 0)
        
        if not updates:
            return (True, "No changes to apply")
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        params.append(user_id)
        
        execute_query(conn, query, params)
        return (True, "User information updated successfully")


# Progress Tracking
class ProgressDAO:
    """Data Access Object for progress-related operations."""
    
    @staticmethod
    @db_transaction
    def update_topic_progress(conn, user_id, chapter_id, topic_id, is_completed):
        """Update a user's progress on a specific topic."""
        if is_completed:
            execute_query(conn, """
                INSERT INTO user_progress (user_id, chapter_id, topic_id, is_completed, completion_date)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, chapter_id, topic_id) 
                DO UPDATE SET is_completed = 1, completion_date = CURRENT_TIMESTAMP
            """, (user_id, chapter_id, topic_id))
        else:
            execute_query(conn, """
                INSERT INTO user_progress (user_id, chapter_id, topic_id, is_completed, completion_date)
                VALUES (?, ?, ?, 0, NULL)
                ON CONFLICT(user_id, chapter_id, topic_id) 
                DO UPDATE SET is_completed = 0, completion_date = NULL
            """, (user_id, chapter_id, topic_id))
        
        return True
    
    @staticmethod
    @db_query
    def get_user_progress(conn, user_id):
        """Get all progress for a user."""
        cursor = execute_query(conn, """
            SELECT chapter_id, topic_id, is_completed, completion_date
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,))
        
        progress = cursor.fetchall()
        
        # Convert to dictionary for easier access
        progress_dict = {}
        for chapter_id, topic_id, is_completed, completion_date in progress:
            if chapter_id not in progress_dict:
                progress_dict[chapter_id] = {}
            
            progress_dict[chapter_id][topic_id] = {
                'is_completed': bool(is_completed),
                'completion_date': completion_date
            }
        
        return progress_dict
    
    @staticmethod
    @db_query
    def get_chapter_completion_stats(conn, user_id):
        """Get completion statistics for each chapter."""
        cursor = execute_query(conn, """
            SELECT 
                chapter_id,
                COUNT(*) as total_topics,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_topics
            FROM user_progress
            WHERE user_id = ?
            GROUP BY chapter_id
        """, (user_id,))
        
        results = cursor.fetchall()
        
        stats = {}
        for chapter_id, total_topics, completed_topics in results:
            completion_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            stats[chapter_id] = {
                'total_topics': total_topics,
                'completed_topics': completed_topics,
                'completion_percentage': completion_percentage
            }
        
        return stats


# Quiz Management
class QuizDAO:
    """Data Access Object for quiz-related operations."""
    
    @staticmethod
    @db_transaction
    def record_result(conn, user_id, total_questions, correct_answers, topics=None):
        """Record a quiz result for a user."""
        execute_query(conn, """
            INSERT INTO quiz_results (user_id, total_questions, correct_answers, topics)
            VALUES (?, ?, ?, ?)
        """, (user_id, total_questions, correct_answers, topics))
        
        return True


# Notes Management
class NotesDAO:
    """Data Access Object for notes-related operations."""
    
    @staticmethod
    @db_transaction
    def add_note(conn, user_id, chapter_id, content):
        """Add a note for a specific chapter."""
        execute_query(conn, """
            INSERT INTO user_notes (user_id, chapter_id, content)
            VALUES (?, ?, ?)
        """, (user_id, chapter_id, content))
        
        return True
    
    @staticmethod
    @db_query
    def get_notes(conn, user_id, chapter_id=None):
        """Get notes for a user, optionally filtered by chapter."""
        if chapter_id:
            cursor = execute_query(conn, """
                SELECT id, chapter_id, content, created_at
                FROM user_notes
                WHERE user_id = ? AND chapter_id = ?
                ORDER BY created_at DESC
            """, (user_id, chapter_id))
        else:
            cursor = execute_query(conn, """
                SELECT id, chapter_id, content, created_at
                FROM user_notes
                WHERE user_id = ?
                ORDER BY chapter_id, created_at DESC
            """, (user_id,))
        
        return cursor.fetchall()


# Admin Statistics
class StatsDAO:
    """Data Access Object for system statistics."""
    
    @staticmethod
    @db_query
    def get_system_statistics(conn):
        """Get system-wide statistics for admin dashboard."""
        stats = {}
        
        # User statistics
        cursor = execute_query(conn, "SELECT COUNT(*) FROM users")
        stats["total_users"] = cursor.fetchone()[0]
        
        # New users in the last 7 days
        cursor = execute_query(conn, "SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '-7 days')")
        stats["new_users_7_days"] = cursor.fetchone()[0]
        
        # Total topics completed
        cursor = execute_query(conn, "SELECT COUNT(*) FROM user_progress WHERE is_completed = 1")
        stats["total_topics_completed"] = cursor.fetchone()[0]
        
        # Total study notes
        cursor = execute_query(conn, "SELECT COUNT(*) FROM user_notes")
        stats["total_notes"] = cursor.fetchone()[0]
        
        # Total quiz attempts
        cursor = execute_query(conn, "SELECT COUNT(*) FROM quiz_results")
        stats["total_quiz_attempts"] = cursor.fetchone()[0]
        
        # Average quiz score
        cursor = execute_query(conn, "SELECT AVG(correct_answers * 100.0 / total_questions) FROM quiz_results")
        avg_score = cursor.fetchone()[0]
        stats["avg_quiz_score"] = avg_score if avg_score is not None else 0
        
        # Most active chapters
        cursor = execute_query(conn, """
            SELECT chapter_id, COUNT(*) as completion_count
            FROM user_progress
            WHERE is_completed = 1
            GROUP BY chapter_id
            ORDER BY completion_count DESC
            LIMIT 5
        """)
        
        stats["most_active_chapters"] = []
        for row in cursor.fetchall():
            stats["most_active_chapters"].append({
                "chapter_id": row[0],
                "completion_count": row[1]
            })
        
        return stats


# Backwards compatibility layer for existing code
# These function versions match the original API signatures and behavior

def get_or_create_user(username, email=None, is_admin=False):
    """Get a user by username or create if not exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, is_admin FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            user_id = user[0]
            
            # Update admin status if needed
            if is_admin and not user[1]:
                cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
                conn.commit()
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
                (username, email, 1 if is_admin else 0)
            )
            conn.commit()
            user_id = cursor.lastrowid
        
        return user_id
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        conn.rollback()
        return None
    finally:
        conn.close()

def update_topic_progress(user_id, chapter_id, topic_id, is_completed):
    """Update a user's progress on a specific topic."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if is_completed:
            cursor.execute("""
                INSERT INTO user_progress (user_id, chapter_id, topic_id, is_completed, completion_date)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, chapter_id, topic_id) 
                DO UPDATE SET is_completed = 1, completion_date = CURRENT_TIMESTAMP
            """, (user_id, chapter_id, topic_id))
        else:
            cursor.execute("""
                INSERT INTO user_progress (user_id, chapter_id, topic_id, is_completed, completion_date)
                VALUES (?, ?, ?, 0, NULL)
                ON CONFLICT(user_id, chapter_id, topic_id) 
                DO UPDATE SET is_completed = 0, completion_date = NULL
            """, (user_id, chapter_id, topic_id))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_progress(user_id):
    """Get all progress for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT chapter_id, topic_id, is_completed, completion_date
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,))
        
        progress = cursor.fetchall()
        
        # Convert to dictionary for easier access
        progress_dict = {}
        for chapter_id, topic_id, is_completed, completion_date in progress:
            if chapter_id not in progress_dict:
                progress_dict[chapter_id] = {}
            
            progress_dict[chapter_id][topic_id] = {
                'is_completed': bool(is_completed),
                'completion_date': completion_date
            }
        
        return progress_dict
    except Exception as e:
        logger.error(f"Error getting user progress: {str(e)}")
        return {}
    finally:
        conn.close()

def get_chapter_completion_stats(user_id):
    """Get completion statistics for each chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                chapter_id,
                COUNT(*) as total_topics,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_topics
            FROM user_progress
            WHERE user_id = ?
            GROUP BY chapter_id
        """, (user_id,))
        
        results = cursor.fetchall()
        
        stats = {}
        for chapter_id, total_topics, completed_topics in results:
            completion_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            stats[chapter_id] = {
                'total_topics': total_topics,
                'completed_topics': completed_topics,
                'completion_percentage': completion_percentage
            }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting completion stats: {str(e)}")
        return {}
    finally:
        conn.close()

def record_quiz_result(user_id, total_questions, correct_answers, topics=None):
    """Record a quiz result for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO quiz_results (user_id, total_questions, correct_answers, topics)
            VALUES (?, ?, ?, ?)
        """, (user_id, total_questions, correct_answers, topics))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error recording quiz result: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def add_user_note(user_id, chapter_id, content):
    """Add a note for a specific chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO user_notes (user_id, chapter_id, content)
            VALUES (?, ?, ?)
        """, (user_id, chapter_id, content))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding user note: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_notes(user_id, chapter_id=None):
    """Get notes for a user, optionally filtered by chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if chapter_id:
            cursor.execute("""
                SELECT id, chapter_id, content, created_at
                FROM user_notes
                WHERE user_id = ? AND chapter_id = ?
                ORDER BY created_at DESC
            """, (user_id, chapter_id))
        else:
            cursor.execute("""
                SELECT id, chapter_id, content, created_at
                FROM user_notes
                WHERE user_id = ?
                ORDER BY chapter_id, created_at DESC
            """, (user_id,))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting user notes: {str(e)}")
        return []
    finally:
        conn.close()

def is_admin(username):
    """Check if a user has admin privileges."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False
    finally:
        conn.close()

def set_admin_status(username, is_admin_status):
    """Grant or revoke admin privileges for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE users SET is_admin = ? WHERE username = ?", 
                      (1 if is_admin_status else 0, username))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error setting admin status: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_users():
    """Get all registered users for admin view."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id, 
                username, 
                email, 
                is_admin, 
                created_at,
                (SELECT COUNT(*) FROM user_progress WHERE user_id = users.id) as progress_count,
                (SELECT COUNT(*) FROM user_notes WHERE user_id = users.id) as notes_count,
                (SELECT COUNT(*) FROM study_sessions WHERE user_id = users.id) as sessions_count,
                (SELECT COUNT(*) FROM quiz_results WHERE user_id = users.id) as quiz_count
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "username": row[1],
                "email": row[2] or "N/A",
                "is_admin": bool(row[3]),
                "created_at": row[4],
                "progress_items": row[5],
                "notes_count": row[6],
                "study_sessions": row[7],
                "quiz_attempts": row[8]
            })
        
        return users
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        return []
    finally:
        conn.close()

def get_user_details(user_id):
    """Get detailed information about a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get user basic info
        cursor.execute("SELECT id, username, email, is_admin, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return None
        
        user_data = {
            "id": user[0],
            "username": user[1],
            "email": user[2] or "N/A",
            "is_admin": bool(user[3]),
            "created_at": user[4],
        }
        
        # Get progress statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_topics,
                SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_topics
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,))
        
        progress = cursor.fetchone()
        if progress:
            total_topics = progress[0] or 0
            completed_topics = progress[1] or 0
            completion_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            
            user_data["progress"] = {
                "total_topics": total_topics,
                "completed_topics": completed_topics,
                "completion_percentage": completion_percentage
            }
        
        # Get quiz statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as attempts,
                AVG(correct_answers * 100.0 / total_questions) as avg_score
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))
        
        quiz_stats = cursor.fetchone()
        if quiz_stats:
            user_data["quiz_stats"] = {
                "attempts": quiz_stats[0],
                "avg_score": quiz_stats[1] or 0
            }
        
        # Get study time statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as sessions,
                SUM(duration_minutes) as total_minutes
            FROM study_sessions
            WHERE user_id = ?
        """, (user_id,))
        
        study_stats = cursor.fetchone()
        if study_stats:
            user_data["study_stats"] = {
                "sessions": study_stats[0],
                "total_minutes": study_stats[1] or 0
            }
        
        return user_data
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        return None
    finally:
        conn.close()

def get_system_statistics():
    """Get system-wide statistics for admin dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        stats = {}
        
        # User statistics
        cursor.execute("SELECT COUNT(*) FROM users")
        stats["total_users"] = cursor.fetchone()[0]
        
        # New users in the last 7 days
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '-7 days')")
        stats["new_users_7_days"] = cursor.fetchone()[0]
        
        # Total topics completed
        cursor.execute("SELECT COUNT(*) FROM user_progress WHERE is_completed = 1")
        stats["total_topics_completed"] = cursor.fetchone()[0]
        
        # Total study notes
        cursor.execute("SELECT COUNT(*) FROM user_notes")
        stats["total_notes"] = cursor.fetchone()[0]
        
        # Total quiz attempts
        cursor.execute("SELECT COUNT(*) FROM quiz_results")
        stats["total_quiz_attempts"] = cursor.fetchone()[0]
        
        # Average quiz score
        cursor.execute("SELECT AVG(correct_answers * 100.0 / total_questions) FROM quiz_results")
        avg_score = cursor.fetchone()[0]
        stats["avg_quiz_score"] = avg_score if avg_score is not None else 0
        
        # Most active chapters
        cursor.execute("""
            SELECT chapter_id, COUNT(*) as completion_count
            FROM user_progress
            WHERE is_completed = 1
            GROUP BY chapter_id
            ORDER BY completion_count DESC
            LIMIT 5
        """)
        
        stats["most_active_chapters"] = []
        for row in cursor.fetchall():
            stats["most_active_chapters"].append({
                "chapter_id": row[0],
                "completion_count": row[1]
            })
        
        return stats
    except Exception as e:
        logger.error(f"Error getting system statistics: {str(e)}")
        return {}
    finally:
        conn.close()

def delete_user(user_id, admin_user_id):
    """Delete a user and all their data (admin only)."""
    # Don't allow deleting yourself
    if user_id == admin_user_id:
        return False, "Cannot delete your own account"
    
    conn = get_connection()
    
    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        cursor = conn.cursor()
        
        # Delete related data first
        cursor.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_notes WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM study_sessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
        
        # Finally delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        # Commit the transaction
        conn.commit()
        
        return True, f"User ID {user_id} and all associated data successfully deleted"
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return False, f"Error deleting user: {str(e)}"
    finally:
        conn.close()

def update_user_metadata(user_id, email=None, is_admin=None):
    """Update user metadata (admin function)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        
        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(1 if is_admin else 0)
        
        if not updates:
            return True, "No changes to apply"
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        params.append(user_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        return True, "User information updated successfully"
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user: {str(e)}")
        return False, f"Error updating user: {str(e)}"
    finally:
        conn.close()

# Initialize database if this script is run directly
if __name__ == "__main__":
    initialize_database()
