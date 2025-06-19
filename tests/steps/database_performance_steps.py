import time
import threading
import concurrent.futures
import sqlite3
from behave import given, when, then
from tests.steps.database_test_utils import (
    create_mock_users, create_mock_progress_entries, 
    create_mock_notes, create_mock_quiz_results
)

@given('the database is initialized with test data')
def step_impl(context):
    """Ensure the database is properly initialized for testing."""
    # This is handled in before_scenario hook, but we verify it here
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    
    # Check if at least the users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone() is not None
    
    conn.close()
    assert table_exists, "Database was not properly initialized"

@given('there are "{num_users:d}" mock users in the database')
def step_impl(context, num_users):
    """Create the specified number of mock users."""
    context.test_user_ids = create_mock_users(context.db_module, num_users)
    
    # Verify user creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count >= num_users, f"Failed to create {num_users} mock users"

@given('there are "{num_regular:d}" regular users and "{num_admin:d}" admin users')
def step_impl(context, num_regular, num_admin):
    """Create regular and admin users for testing."""
    # Create regular users
    context.regular_user_ids = create_mock_users(context.db_module, num_regular, False)
    
    # Create admin users
    context.admin_user_ids = create_mock_users(context.db_module, num_admin, True)
    
    # Verify user creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    regular_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Account for the default admin user that's created during initialization
    assert regular_count >= num_regular, f"Failed to create {num_regular} regular users"
    assert admin_count >= num_admin, f"Failed to create {num_admin} admin users"

@given('there are "{num_entries:d}" progress entries in the database')
def step_impl(context, num_entries):
    """Create mock progress entries in the database."""
    # We need at least some users to create progress entries for
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 10)
    
    # Calculate how many entries per user to create
    entries_per_user = max(1, num_entries // len(context.test_user_ids))
    
    # Create progress entries
    total_created = create_mock_progress_entries(
        context.db_module, context.test_user_ids, entries_per_user
    )
    
    # Verify progress entry creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_progress")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count >= num_entries, f"Failed to create {num_entries} progress entries"

@given('the database contains "{num_records:d}" records in the "{table}" table')
def step_impl(context, num_records, table):
    """Create the specified number of records in the given table."""
    # We need users to create records for
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 
                                               max(10, num_records // 10))
    
    # Calculate records per user
    records_per_user = max(1, num_records // len(context.test_user_ids))
    
    # Create appropriate records based on the table
    if table == 'users':
        # We've already created some users, so create more if needed
        additional_users = max(0, num_records - len(context.test_user_ids))
        if additional_users > 0:
            more_user_ids = create_mock_users(context.db_module, additional_users)
            context.test_user_ids.extend(more_user_ids)
    elif table == 'user_progress':
        create_mock_progress_entries(context.db_module, context.test_user_ids, records_per_user)
    elif table == 'user_notes':
        create_mock_notes(context.db_module, context.test_user_ids, records_per_user)
    elif table == 'quiz_results':
        create_mock_quiz_results(context.db_module, context.test_user_ids, records_per_user)
    else:
        raise ValueError(f"Unsupported table: {table}")
    
    # Verify record creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    conn.close()
    
    context.execution_info = {
        'table': table,
        'expected_records': num_records,
        'actual_records': count
    }
    
    assert count >= num_records, f"Failed to create {num_records} records in {table}"

@when('I create "{num_users:d}" new users in the database')
def step_impl(context, num_users):
    """Create the specified number of new users and measure performance."""
    # Start timing
    context.start_time = time.time()
    
    # Create users
    new_user_ids = create_mock_users(context.db_module, num_users)
    context.test_user_ids.extend(new_user_ids)
    
    # End timing
    context.end_time = time.time()
    context.execution_time = context.end_time - context.start_time
    
    print(f"Created {num_users} users in {context.execution_time:.3f} seconds")

@when('I retrieve all users from the database')
def step_impl(context):
    """Retrieve all users and measure performance."""
    # Start timing
    context.start_time = time.time()
    
    # Get all users
    if hasattr(context.db_module, 'get_all_users'):
        context.retrieved_users = context.db_module.get_all_users()
    else:
        # Fallback if function doesn't exist
        conn = context.db_module.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        context.retrieved_users = cursor.fetchall()
        conn.close()
    
    # End timing
    context.end_time = time.time()
    context.execution_time = context.end_time - context.start_time
    
    print(f"Retrieved {len(context.retrieved_users)} users in {context.execution_time:.3f} seconds")

@when('I add "{num_entries:d}" new progress entries')
def step_impl(context, num_entries):
    """Add new progress entries and measure performance."""
    # We need users to create progress entries for
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 10)
    
    # Calculate entries per user
    entries_per_user = max(1, num_entries // len(context.test_user_ids))
    
    # Start timing
    context.start_time = time.time()
    
    # Create progress entries
    total_created = create_mock_progress_entries(
        context.db_module, context.test_user_ids, entries_per_user
    )
    
    # End timing
    context.end_time = time.time()
    context.execution_time = context.end_time - context.start_time
    
    print(f"Created {total_created} progress entries in {context.execution_time:.3f} seconds")

@when('I execute a query to select all records from the "{table}" table')
def step_impl(context, table):
    """Execute a select query and measure performance."""
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    
    # Start timing
    context.start_time = time.time()
    
    # Execute query
    cursor.execute(f"SELECT * FROM {table}")
    context.query_results = cursor.fetchall()
    
    # End timing
    context.end_time = time.time()
    context.execution_time = context.end_time - context.start_time
    
    conn.close()
    
    print(f"Query executed on table {table} with {len(context.query_results)} results " +
          f"in {context.execution_time:.3f} seconds")

@then('all user creation operations should complete within "{max_time:f}" second')
def step_impl(context, max_time):
    """Verify user creation operations completed within the specified time."""
    assert context.execution_time <= max_time, \
        f"User creation took {context.execution_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"

@then('the database should contain "{expected_count:d}" total users')
def step_impl(context, expected_count):
    """Verify the database contains the expected number of users."""
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    actual_count = cursor.fetchone()[0]
    conn.close()
    
    assert actual_count == expected_count, \
        f"Database contains {actual_count} users, but expected {expected_count}"

@then('the operation should complete within "{max_time:f}" seconds')
def step_impl(context, max_time):
    """Verify an operation completed within the specified time."""
    assert context.execution_time <= max_time, \
        f"Operation took {context.execution_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"

@then('the data should be correctly returned')
def step_impl(context):
    """Verify data was correctly returned."""
    assert hasattr(context, 'retrieved_users'), "No user data was retrieved"
    assert len(context.retrieved_users) > 0, "No users were returned"
    
    # If we're using the get_all_users function, the result is a list of dicts
    if isinstance(context.retrieved_users[0], dict):
        assert 'username' in context.retrieved_users[0], "User data missing username field"
    # Otherwise it's raw tuples from the database
    else:
        assert len(context.retrieved_users[0]) >= 2, "User data has insufficient fields"

@then('all progress tracking operations should complete within "{max_time:f}" second')
def step_impl(context, max_time):
    """Verify progress tracking operations completed within the specified time."""
    assert context.execution_time <= max_time, \
        f"Progress tracking operations took {context.execution_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"

@then('the progress retrieval for a user should complete within "{max_time:f}" seconds')
def step_impl(context, max_time):
    """Verify progress retrieval for a single user completes within the specified time."""
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        raise ValueError("No test users available for progress retrieval test")
    
    user_id = context.test_user_ids[0]
    
    # Start timing
    start_time = time.time()
    
    # Get user progress
    user_progress = context.db_module.get_user_progress(user_id)
    
    # End timing
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Retrieved progress for user {user_id} in {execution_time:.3f} seconds")
    
    assert execution_time <= float(max_time), \
        f"Progress retrieval took {execution_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"

@then('the query should complete within "{max_time:f}" seconds')
def step_impl(context, max_time):
    """Verify a query completed within the specified time."""
    assert context.execution_time <= max_time, \
        f"Query execution took {context.execution_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"
