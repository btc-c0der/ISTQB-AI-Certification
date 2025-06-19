import os
import sqlite3
from pathlib import Path

# Define database directory and file path
DB_DIR = Path(__file__).parent
DB_FILE = DB_DIR / "istqb_portal.db"

def ensure_db_exists():
    """Ensure the database directory and file exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    
    return str(DB_FILE)

def get_connection():
    """Get a connection to the SQLite database."""
    db_path = ensure_db_exists()
    return sqlite3.connect(db_path)

def initialize_database():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if we need to migrate the users table to add is_admin column
    need_migration = False
    
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table_exists = cursor.fetchone() is not None
    
    if users_table_exists:
        # Check if is_admin column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "is_admin" not in column_names:
            print("Migrating users table to add is_admin column...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            need_migration = True
    
    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        is_admin BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create user_progress table to track completed chapters and topics
    cursor.execute('''
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
    ''')
    
    # Create user_notes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chapter_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create study_sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chapter_id TEXT NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        duration_minutes INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create quiz_results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_questions INTEGER NOT NULL,
        correct_answers INTEGER NOT NULL,
        topics TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Create default admin user
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        cursor.execute(
            "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
            ("admin", "admin@example.com", 1)
        )
        print("Created default admin user. Username: admin")
    elif need_migration:
        # Update existing admin user during migration
        cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
        print("Updated admin user with admin privileges")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized successfully.")

# User management functions
def get_or_create_user(username, email=None, is_admin=False):
    """Get a user by username or create if not exists."""
    conn = get_connection()
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
    
    conn.close()
    return user_id

# Progress tracking functions
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
        print(f"Error updating progress: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user_progress(user_id):
    """Get all progress for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT chapter_id, topic_id, is_completed, completion_date
        FROM user_progress
        WHERE user_id = ?
    """, (user_id,))
    
    progress = cursor.fetchall()
    conn.close()
    
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

def get_chapter_completion_stats(user_id):
    """Get completion statistics for each chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    conn.close()
    
    stats = {}
    for chapter_id, total_topics, completed_topics in results:
        completion_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
        stats[chapter_id] = {
            'total_topics': total_topics,
            'completed_topics': completed_topics,
            'completion_percentage': completion_percentage
        }
    
    return stats

def record_quiz_result(user_id, total_questions, correct_answers, topics=None):
    """Record a quiz result for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO quiz_results (user_id, total_questions, correct_answers, topics)
        VALUES (?, ?, ?, ?)
    """, (user_id, total_questions, correct_answers, topics))
    
    conn.commit()
    conn.close()
    return True

def add_user_note(user_id, chapter_id, content):
    """Add a note for a specific chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_notes (user_id, chapter_id, content)
        VALUES (?, ?, ?)
    """, (user_id, chapter_id, content))
    
    conn.commit()
    conn.close()
    return True

def get_user_notes(user_id, chapter_id=None):
    """Get notes for a user, optionally filtered by chapter."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    
    notes = cursor.fetchall()
    conn.close()
    
    return notes

# Admin functions
def is_admin(username):
    """Check if a user has admin privileges."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0]:
        return True
    return False

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
        print(f"Error setting admin status: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_users():
    """Get all registered users for admin view."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    
    conn.close()
    return users

def get_user_details(user_id):
    """Get detailed information about a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get user basic info
    cursor.execute("SELECT id, username, email, is_admin, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
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
    
    conn.close()
    return user_data

def get_system_statistics():
    """Get system-wide statistics for admin dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
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
    
    conn.close()
    return stats

def delete_user(user_id, admin_user_id):
    """Delete a user and all their data (admin only)."""
    # Don't allow deleting yourself
    if user_id == admin_user_id:
        return False, "Cannot delete your own account"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        
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
        return False, f"Error updating user: {str(e)}"
    finally:
        conn.close()

# Initialize database if this script is run directly
if __name__ == "__main__":
    initialize_database()
