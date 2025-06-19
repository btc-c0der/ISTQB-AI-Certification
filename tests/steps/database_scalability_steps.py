import time
import random
import string
import threading
import concurrent.futures
import sqlite3
from behave import given, when, then
from tests.steps.database_test_utils import (
    create_mock_users, create_mock_progress_entries,
    create_mock_notes, create_mock_quiz_results
)

@given('the database has "{num_users:d}" users with progress data')
def step_impl(context, num_users):
    """Create a specified number of users with progress data."""
    # Create users
    context.test_user_ids = create_mock_users(context.db_module, num_users)
    
    # Add some progress data for each user
    entries_per_user = 5
    create_mock_progress_entries(context.db_module, context.test_user_ids, entries_per_user)
    
    print(f"Created {num_users} users with progress data")

@when('"{num_concurrent:d}" users simultaneously access their progress data')
def step_impl(context, num_concurrent):
    """Simulate concurrent users accessing their progress data.""" 
    # Select a subset of users if we have more than requested
    if len(context.test_user_ids) > num_concurrent:
        user_ids_to_use = random.sample(context.test_user_ids, num_concurrent)
    else:
        user_ids_to_use = context.test_user_ids
    
    # Keep track of execution times
    context.execution_times = []
    
    def access_progress(user_id):
        """Function to run for each user thread."""
        start_time = time.time()
        
        # Get user progress
        progress = context.db_module.get_user_progress(user_id)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return execution_time, progress is not None
    
    # Use ThreadPoolExecutor to run sessions concurrently
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        future_to_user = {
            executor.submit(access_progress, user_id): user_id 
            for user_id in user_ids_to_use
        }
        
        # Collect results
        for future in concurrent.futures.as_completed(future_to_user):
            user_id = future_to_user[future]
            try:
                execution_time, success = future.result()
                context.execution_times.append((user_id, execution_time, success))
            except Exception as e:
                print(f"User {user_id} generated an exception: {e}")
                context.execution_times.append((user_id, 0, False))
    
    end_time = time.time()
    context.total_execution_time = end_time - start_time
    
    print(f"Completed {num_concurrent} concurrent progress requests " +
          f"in {context.total_execution_time:.3f} seconds")

@then('all requests should complete within "{max_time:f}" seconds')
def step_impl(context, max_time):
    """Verify all requests completed within the specified time."""
    assert context.total_execution_time <= float(max_time), \
        f"Total execution time {context.total_execution_time:.3f} seconds " + \
        f"exceeds maximum allowed time of {max_time} seconds"

@then('the system should maintain response times within "{variance:d}%" variance')
def step_impl(context, variance):
    """Verify response time variance is within acceptable limits."""
    times = [t[1] for t in context.execution_times if t[1] > 0]
    
    if not times:
        raise ValueError("No valid execution times recorded")
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    # Calculate the variance as a percentage of the average
    max_variance_percentage = ((max_time - avg_time) / avg_time) * 100
    
    print(f"Average response time: {avg_time:.3f}s, Maximum: {max_time:.3f}s, " +
          f"Variance: {max_variance_percentage:.2f}%")
    
    assert max_variance_percentage <= float(variance), \
        f"Response time variance {max_variance_percentage:.2f}% " + \
        f"exceeds maximum allowed {variance}%"

@when('I add "{additional:d}" more records to the "{table}" table')
def step_impl(context, additional, table):
    """Add more records to a table and measure performance impact."""
    # First get baseline query performance
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    
    # Baseline query
    baseline_start = time.time()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    initial_count = cursor.fetchone()[0]
    baseline_end = time.time()
    
    context.baseline_query_time = baseline_end - baseline_start
    print(f"Baseline query on {table} took {context.baseline_query_time:.6f}s " +
          f"with {initial_count} records")
    
    # Now add the additional records
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 
                                               max(10, additional // 100))
    
    records_per_user = max(1, additional // len(context.test_user_ids))
    
    # Create appropriate records based on the table
    if table == 'users':
        additional_user_ids = create_mock_users(context.db_module, additional)
        context.test_user_ids.extend(additional_user_ids)
    elif table == 'user_progress':
        create_mock_progress_entries(context.db_module, context.test_user_ids, records_per_user)
    elif table == 'user_notes':
        create_mock_notes(context.db_module, context.test_user_ids, records_per_user)
    elif table == 'quiz_results':
        create_mock_quiz_results(context.db_module, context.test_user_ids, records_per_user)
    else:
        raise ValueError(f"Unsupported table: {table}")
    
    # Verify record creation
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    new_count = cursor.fetchone()[0]
    records_added = new_count - initial_count
    
    print(f"Added {records_added} records to {table}, new total: {new_count}")
    
    # Now measure the query time again with more records
    final_start = time.time()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    cursor.fetchall()
    final_end = time.time()
    
    context.final_query_time = final_end - final_start
    conn.close()
    
    print(f"Query after adding records took {context.final_query_time:.6f}s")
    
    context.table = table
    context.initial_count = initial_count
    context.final_count = new_count

@then('the query to retrieve all records should not slow down by more than "{factor:f}"')
def step_impl(context, factor):
    """Verify query performance doesn't degrade more than the specified factor."""
    # Calculate the slowdown factor
    if context.baseline_query_time > 0:
        slowdown = context.final_query_time / context.baseline_query_time
    else:
        slowdown = 1.0
    
    # Calculate the data growth factor
    data_growth = context.final_count / max(1, context.initial_count)
    
    print(f"Query slowdown factor: {slowdown:.2f}x with data growth of {data_growth:.2f}x")
    print(f"Baseline time: {context.baseline_query_time:.6f}s, Final time: {context.final_query_time:.6f}s")
    
    assert slowdown <= float(factor), \
        f"Query slowdown factor {slowdown:.2f}x exceeds maximum allowed {factor}x"

@given('the database contains "{user_count:d}" user records')
def step_impl(context, user_count):
    """Create a specified number of user records."""
    context.test_user_ids = create_mock_users(context.db_module, user_count)
    
    # Verify user creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"Created {user_count} user records, actual count: {count}")
    context.user_count = count

@given('"{progress_count:d}" progress tracking entries')
def step_impl(context, progress_count):
    """Create a specified number of progress tracking entries."""
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 100)
    
    entries_per_user = max(1, progress_count // len(context.test_user_ids))
    create_mock_progress_entries(context.db_module, context.test_user_ids, entries_per_user)
    
    # Verify progress entry creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_progress")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"Created progress tracking entries, actual count: {count}")
    context.progress_count = count

@given('"{quiz_count:d}" quiz result records')
def step_impl(context, quiz_count):
    """Create a specified number of quiz result records."""
    if not hasattr(context, 'test_user_ids') or not context.test_user_ids:
        context.test_user_ids = create_mock_users(context.db_module, 100)
    
    results_per_user = max(1, quiz_count // len(context.test_user_ids))
    create_mock_quiz_results(context.db_module, context.test_user_ids, results_per_user)
    
    # Verify quiz result creation
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quiz_results")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"Created quiz result records, actual count: {count}")
    context.quiz_count = count

@when('I perform a complete database backup')
def step_impl(context):
    """Perform a complete database backup and measure performance."""
    import tempfile
    import sqlite3
    
    # Create a temporary file for the backup
    backup_file = tempfile.NamedTemporaryFile(delete=False)
    context.backup_path = backup_file.name
    backup_file.close()
    
    # Start timing
    start_time = time.time()
    
    # Perform the backup
    source_conn = context.db_module.get_connection()
    dest_conn = sqlite3.connect(context.backup_path)
    
    source_conn.backup(dest_conn)
    
    source_conn.close()
    dest_conn.close()
    
    # End timing
    end_time = time.time()
    context.backup_time = end_time - start_time
    
    print(f"Database backup completed in {context.backup_time:.3f} seconds")

@then('the backup should complete within "{max_time:d}" seconds')
def step_impl(context, max_time):
    """Verify the backup completed within the specified time."""
    assert context.backup_time <= float(max_time), \
        f"Backup took {context.backup_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"

@then('the backup file should be successfully created')
def step_impl(context):
    """Verify the backup file was successfully created."""
    import os
    
    # Check that the file exists and has a size greater than zero
    assert os.path.exists(context.backup_path), "Backup file does not exist"
    assert os.path.getsize(context.backup_path) > 0, "Backup file is empty"
    
    print(f"Backup file successfully created at {context.backup_path} " +
          f"({os.path.getsize(context.backup_path)} bytes)")

@then('the database can be restored from backup within "{max_time:d}" seconds')
def step_impl(context, max_time):
    """Verify the database can be restored from backup within the specified time."""
    import tempfile
    import sqlite3
    import os
    
    # Create a temporary directory for the restored database
    restore_dir = tempfile.mkdtemp()
    restore_path = os.path.join(restore_dir, "restored.db")
    
    # Start timing
    start_time = time.time()
    
    # Perform the restore
    source_conn = sqlite3.connect(context.backup_path)
    dest_conn = sqlite3.connect(restore_path)
    
    source_conn.backup(dest_conn)
    
    source_conn.close()
    dest_conn.close()
    
    # End timing
    end_time = time.time()
    context.restore_time = end_time - start_time
    
    # Clean up
    os.unlink(context.backup_path)
    os.unlink(restore_path)
    os.rmdir(restore_dir)
    
    print(f"Database restore completed in {context.restore_time:.3f} seconds")
    
    assert context.restore_time <= float(max_time), \
        f"Restore took {context.restore_time:.3f} seconds, " + \
        f"which exceeds the maximum allowed time of {max_time} seconds"
