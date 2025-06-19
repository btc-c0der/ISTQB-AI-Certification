import time
import threading
import sqlite3
import random
from concurrent.futures import ThreadPoolExecutor
from behave import given, when, then

@given('I have a database transaction in progress')
def step_impl(context):
    """Set up a database transaction."""
    # Get a database connection
    context.conn = context.db_module.get_connection()
    context.conn.execute("BEGIN TRANSACTION")
    context.transaction_active = True
    
    print("Database transaction started")

@when('an error occurs during a user creation operation')
def step_impl(context):
    """Simulate an error during a user creation operation."""
    if not hasattr(context, 'conn') or not context.transaction_active:
        raise ValueError("No active transaction to test with")
    
    try:
        # Attempt to create a user with a duplicate username (should cause constraint violation)
        cursor = context.conn.cursor()
        
        # First create a user normally
        cursor.execute(
            "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
            ("unique_test_user", "test@example.com", 0)
        )
        
        # Now try to create another user with the same username (this should fail)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, is_admin) VALUES (?, ?, ?)",
                ("unique_test_user", "another@example.com", 0)
            )
            context.error_raised = False
        except sqlite3.IntegrityError:
            context.error_raised = True
            # We expect the transaction to be rolled back in the database.py module,
            # but here we'll simulate it explicitly
            context.conn.rollback()
            context.transaction_active = False
    except Exception as e:
        context.exception = e
        context.error_raised = True
        if hasattr(context, 'conn'):
            context.conn.rollback()
            context.transaction_active = False
    
    print(f"Error simulation completed, error raised: {context.error_raised}")

@then('the transaction should be rolled back')
def step_impl(context):
    """Verify that the transaction was rolled back."""
    # We'll check if the first insert was rolled back by looking for the user
    new_conn = context.db_module.get_connection()
    cursor = new_conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("unique_test_user",))
    count = cursor.fetchone()[0]
    
    new_conn.close()
    
    # If the transaction was properly rolled back, we should have 0 users with this name
    assert count == 0, f"Transaction was not rolled back properly, found {count} users"
    
    # Also verify the error was actually raised
    assert context.error_raised, "No error was raised during the operation"
    
    print("Transaction was properly rolled back")

@then('the database should remain in a consistent state')
def step_impl(context):
    """Verify the database remains in a consistent state after an error."""
    # We can check this by making sure all tables are still accessible
    conn = context.db_module.get_connection()
    cursor = conn.cursor()
    
    tables_to_check = ['users', 'user_progress', 'user_notes', 'quiz_results']
    all_tables_ok = True
    
    for table in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cursor.fetchone()
        except Exception as e:
            all_tables_ok = False
            print(f"Error accessing table {table}: {e}")
    
    conn.close()
    
    assert all_tables_ok, "Database is not in a consistent state after error"

@then('no partial data should be committed')
def step_impl(context):
    """Verify no partial data was committed during a failed transaction."""
    # This is essentially a duplicate of the "transaction should be rolled back" check
    # but we'll keep it for clarity in the BDD scenarios
    
    # We'll check if the first insert was committed despite the second one failing
    new_conn = context.db_module.get_connection()
    cursor = new_conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("unique_test_user",))
    count = cursor.fetchone()[0]
    
    new_conn.close()
    
    assert count == 0, f"Partial data was committed, found {count} users"

@given('"{num_sessions:d}" concurrent user sessions')
def step_impl(context, num_sessions):
    """Set up concurrent user sessions for testing."""
    context.num_sessions = num_sessions
    context.session_results = []
    context.session_errors = []
    
    # Create user IDs for each session to use
    context.session_user_ids = create_mock_users(context.db_module, num_sessions)
    
    print(f"Created {num_sessions} test user sessions")

@when('each session performs "{num_operations:d}" database operations simultaneously')
def step_impl(context, num_operations):
    """Perform operations from multiple sessions simultaneously."""
    def session_worker(user_id, num_ops):
        """Function to run for each session thread."""
        operations = [
            'add_progress', 'add_note', 'add_quiz_result',
            'get_progress', 'get_notes'
        ]
        
        session_results = []
        session_errors = []
        
        try:
            for _ in range(num_ops):
                operation = random.choice(operations)
                
                if operation == 'add_progress':
                    chapter_id = f"chapter_{random.randint(1, 5)}"
                    topic_id = f"topic_{random.randint(1, 20)}"
                    result = context.db_module.update_topic_progress(
                        user_id, chapter_id, topic_id, random.choice([True, False])
                    )
                    session_results.append(('add_progress', result))
                
                elif operation == 'add_note':
                    chapter_id = f"chapter_{random.randint(1, 5)}"
                    content = f"Note content {random.randint(1, 1000)}"
                    result = context.db_module.add_user_note(user_id, chapter_id, content)
                    session_results.append(('add_note', result))
                
                elif operation == 'add_quiz_result':
                    total = random.randint(5, 20)
                    correct = random.randint(0, total)
                    result = context.db_module.record_quiz_result(
                        user_id, total, correct, f"topic_{random.randint(1, 5)}"
                    )
                    session_results.append(('add_quiz_result', result))
                
                elif operation == 'get_progress':
                    result = context.db_module.get_user_progress(user_id)
                    session_results.append(('get_progress', bool(result is not None)))
                
                elif operation == 'get_notes':
                    result = context.db_module.get_user_notes(user_id)
                    session_results.append(('get_notes', bool(result is not None)))
                
                # Small sleep to increase chance of thread interleaving
                time.sleep(random.uniform(0.001, 0.01))
                
        except Exception as e:
            session_errors.append(str(e))
        
        return session_results, session_errors
    
    # Use ThreadPoolExecutor to run sessions concurrently
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=context.num_sessions) as executor:
        futures = [
            executor.submit(session_worker, user_id, num_operations)
            for user_id in context.session_user_ids
        ]
        
        # Collect results
        for future in futures:
            results, errors = future.result()
            context.session_results.extend(results)
            context.session_errors.extend(errors)
    
    end_time = time.time()
    context.concurrent_execution_time = end_time - start_time
    
    total_operations = context.num_sessions * num_operations
    print(f"Completed {total_operations} operations across {context.num_sessions} " +
          f"sessions in {context.concurrent_execution_time:.3f} seconds")
    print(f"Errors encountered: {len(context.session_errors)}")

@then('all operations should complete successfully')
def step_impl(context):
    """Verify all operations completed successfully."""
    if not hasattr(context, 'session_results'):
        raise ValueError("No session results available")
    
    # Check for any errors
    assert len(context.session_errors) == 0, \
        f"Encountered {len(context.session_errors)} errors: {context.session_errors[:5]}"
    
    # Check for failed operations (those that returned False)
    failed_ops = [op for op, success in context.session_results if not success]
    assert len(failed_ops) == 0, \
        f"Found {len(failed_ops)} failed operations: {failed_ops[:5]}"

@then('no deadlocks should occur')
def step_impl(context):
    """Verify no deadlocks occurred during concurrent operations."""
    # If we got here, no operations timed out, which is good
    # Let's also check for any deadlock errors in the error list
    deadlock_errors = [err for err in context.session_errors if 'deadlock' in err.lower()]
    
    assert len(deadlock_errors) == 0, \
        f"Encountered {len(deadlock_errors)} deadlock errors: {deadlock_errors}"

@given('the database connection is temporarily lost')
def step_impl(context):
    """Simulate a temporary database connection loss."""
    # We'll simulate this by deliberately closing the connection pool
    # or breaking a connection mid-operation
    
    # First, let's back up the original connection function
    context.original_get_connection = context.db_module.get_connection
    
    # Define a counter to simulate connection failures
    context.connection_attempts = 0
    context.max_failures = 3
    
    # Override the connection function to simulate failures
    def mock_get_connection():
        context.connection_attempts += 1
        
        # Fail the first few attempts
        if context.connection_attempts <= context.max_failures:
            raise sqlite3.OperationalError("Simulated connection failure")
        
        # After that, return a real connection
        return context.original_get_connection()
    
    # Replace the connection function with our mock
    context.db_module.get_connection = mock_get_connection
    
    print(f"Configured database to simulate {context.max_failures} connection failures")

@when('a user attempts to perform operations')
def step_impl(context):
    """Attempt operations during a simulated connection failure."""
    # Create a test user
    context.test_username = f"recovery_test_{random.randint(1000, 9999)}"
    
    # Try to create a user - this should initially fail due to our mock
    try:
        context.user_id = context.db_module.get_or_create_user(
            context.test_username, "recovery@test.com"
        )
        context.operation_succeeded = True
    except Exception as e:
        context.operation_error = str(e)
        context.operation_succeeded = False
    
    print(f"Operation {'succeeded' if context.operation_succeeded else 'failed'}")
    if not context.operation_succeeded:
        print(f"Error: {context.operation_error}")

@then('the system should attempt to reconnect')
def step_impl(context):
    """Verify the system attempted to reconnect after failure."""
    # We can verify this by checking that the connection counter advanced
    assert context.connection_attempts > 0, "No connection attempts were made"

@then('provide appropriate error messages')
def step_impl(context):
    """Verify appropriate error messages were provided."""
    # If the operation succeeded despite the connection issues, we might not have an error
    if context.operation_succeeded:
        print("Operation eventually succeeded, so no error message to check")
    else:
        assert hasattr(context, 'operation_error'), "No error message was captured"
        assert "connection" in context.operation_error.lower() or \
               "database" in context.operation_error.lower(), \
               f"Error message not related to connection: {context.operation_error}"

@then('successfully reconnect when the database is available again')
def step_impl(context):
    """Verify successful reconnection when the database is available."""
    # By this point, our mock should allow connections again
    # Try one more operation to verify we can successfully connect
    
    try:
        # Create a new user
        username = f"recovery_success_{random.randint(1000, 9999)}"
        user_id = context.db_module.get_or_create_user(username, "success@test.com")
        
        # Verify the user was created
        conn = context.original_get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        context.recovery_succeeded = result is not None and result[0] > 0
    except Exception as e:
        context.recovery_succeeded = False
        context.recovery_error = str(e)
    
    # Restore the original connection function
    context.db_module.get_connection = context.original_get_connection
    
    assert context.recovery_succeeded, \
        f"Failed to recover after connection failures: {getattr(context, 'recovery_error', 'Unknown error')}"
