import os
import sys
import time
import sqlite3
import threading
import random
import string
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from behave import given, when, then, step
from typing import List, Dict, Any

# Add the parent directory to sys.path to import the database module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import both database implementations for testing
import db.database as original_db
import db.database_refactored as refactored_db

# Functions to help with test data generation
def generate_random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def generate_random_email() -> str:
    """Generate a random email address."""
    domain = random.choice(['example.com', 'test.org', 'mail.net', 'fake.io'])
    username = generate_random_string(8)
    return f"{username}@{domain}"

def create_mock_users(db_module, count: int, is_admin: bool = False) -> List[int]:
    """Create a specified number of mock users in the database."""
    user_ids = []
    for i in range(count):
        username = f"testuser_{generate_random_string(8)}"
        email = generate_random_email()
        user_id = db_module.get_or_create_user(username, email, is_admin)
        user_ids.append(user_id)
    return user_ids

def create_mock_progress_entries(db_module, user_ids: List[int], count_per_user: int) -> int:
    """Create mock progress entries for the specified users."""
    total_entries = 0
    chapters = ['chapter1', 'chapter2', 'chapter3', 'chapter4', 'chapter5']
    
    for user_id in user_ids:
        for _ in range(count_per_user):
            chapter_id = random.choice(chapters)
            topic_id = f"topic_{generate_random_string(5)}"
            is_completed = random.choice([True, False])
            
            db_module.update_topic_progress(user_id, chapter_id, topic_id, is_completed)
            total_entries += 1
    
    return total_entries

def create_mock_notes(db_module, user_ids: List[int], count_per_user: int) -> int:
    """Create mock notes for the specified users."""
    total_notes = 0
    chapters = ['chapter1', 'chapter2', 'chapter3', 'chapter4', 'chapter5']
    
    for user_id in user_ids:
        for _ in range(count_per_user):
            chapter_id = random.choice(chapters)
            content = f"Test note content: {generate_random_string(50)}"
            
            db_module.add_user_note(user_id, chapter_id, content)
            total_notes += 1
    
    return total_notes

def create_mock_quiz_results(db_module, user_ids: List[int], count_per_user: int) -> int:
    """Create mock quiz results for the specified users."""
    total_results = 0
    topics = ['AI testing fundamentals', 'ML models', 'Test approaches', 'Quality characteristics']
    
    for user_id in user_ids:
        for _ in range(count_per_user):
            total_questions = random.randint(5, 20)
            correct_answers = random.randint(0, total_questions)
            topic = random.choice(topics)
            
            db_module.record_quiz_result(user_id, total_questions, correct_answers, topic)
            total_results += 1
    
    return total_results

# Behave setup
def before_scenario(context, scenario):
    """Set up test environment before each scenario."""
    # Create a temporary directory for the test database
    context.test_dir = tempfile.mkdtemp()
    
    # Select which DB implementation to test based on tags
    if 'refactored' in scenario.tags:
        context.db_module = refactored_db
    else:
        context.db_module = original_db
    
    # Back up the original database file path constants
    context.original_db_dir = context.db_module.DB_DIR
    context.original_db_file = context.db_module.DB_FILE
    
    # Set the database file paths for testing
    context.db_module.DB_DIR = Path(context.test_dir)
    context.db_module.DB_FILE = context.db_module.DB_DIR / "test_db.db"
    
    # Initialize the database
    context.db_module.initialize_database()
    
    # Store performance timings
    context.start_time = None
    context.end_time = None
    context.execution_times = []
    
    # Store created test data for cleanup
    context.test_user_ids = []
    context.temp_files = []

def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Restore original database file path constants
    if hasattr(context, 'original_db_dir'):
        context.db_module.DB_DIR = context.original_db_dir
        context.db_module.DB_FILE = context.original_db_file
    
    # Remove the temporary directory
    if hasattr(context, 'test_dir'):
        shutil.rmtree(context.test_dir)

# Register hooks with behave
def before_all(context):
    context.config.setup_logging()

def after_all(context):
    pass
