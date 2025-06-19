# Non-Functional Database Tests

This directory contains non-functional BDD (Behavior-Driven Development) tests for the database module. These tests verify performance, reliability, security, and scalability aspects of the database implementation.

## Test Categories

The tests are organized into four main categories:

1. **Performance Tests**: Verify that database operations complete within acceptable time limits.
2. **Reliability Tests**: Ensure the database handles errors gracefully and maintains data consistency.
3. **Security Tests**: Check that the database prevents unauthorized access and data leakage.
4. **Scalability Tests**: Validate that the database performs well as data volume increases.

## Running the Tests

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements-test.txt
```

### Running All Tests

To run all non-functional tests:

```bash
python tests/run_nft_tests.py
```

### Running Specific Test Categories

To run only tests from a specific category:

```bash
python tests/run_nft_tests.py --tags performance
python tests/run_nft_tests.py --tags reliability
python tests/run_nft_tests.py --tags security
python tests/run_nft_tests.py --tags scalability
```

### Running Specific Feature Files

To run specific feature files:

```bash
python tests/run_nft_tests.py --features database_performance.feature
```

### Output Formats

You can generate test reports in different formats:

```bash
# Generate JUnit XML reports
python tests/run_nft_tests.py --junit

# Generate JSON report
python tests/run_nft_tests.py --format json --output reports/test_results.json

# Generate plain text report
python tests/run_nft_tests.py --format plain --output reports/test_results.txt
```

### Additional Options

- `--verbose`: Show more detailed output
- `--no-capture`: Don't capture stdout/stderr during test execution
- `--stop`: Stop on first test failure

## Test Descriptions

### Performance Tests

Tests that verify database operations complete within acceptable time limits:

- Fast user creation
- Fast user retrieval
- Fast progress tracking
- Database query performance under varying loads

### Reliability Tests

Tests that ensure the database handles errors gracefully and maintains data consistency:

- Transaction rollback on error
- Concurrent user operations
- Database connection recovery
- Error handling for invalid inputs

### Security Tests

Tests that check the database prevents unauthorized access and data leakage:

- Admin privilege enforcement
- SQL injection prevention
- Sensitive data handling
- Permission boundaries

### Scalability Tests

Tests that validate the database performs well as data volume increases:

- Performance under growing data volume
- Concurrent user access scaling
- Database size impact on backup/restore

## Customizing Tests

To modify test parameters or add new tests:

1. Edit or add feature files in the `tests/features/` directory
2. Implement step definitions in the `tests/steps/` directory
3. Update the test utilities in `tests/steps/database_test_utils.py`
