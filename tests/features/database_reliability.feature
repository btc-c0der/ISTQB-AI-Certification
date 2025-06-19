Feature: Database Reliability and Resilience
  As an application administrator
  I want to ensure the database operations are reliable and resilient to failures
  So that the application data remains consistent and available

  Background:
    Given the database is initialized with test data
    And there are "50" mock users in the database

  @reliability
  Scenario: Transaction rollback on error
    Given I have a database transaction in progress
    When an error occurs during a user creation operation
    Then the transaction should be rolled back
    And the database should remain in a consistent state
    And no partial data should be committed

  @reliability
  Scenario: Concurrent user operations
    Given "10" concurrent user sessions
    When each session performs "20" database operations simultaneously
    Then all operations should complete successfully
    And the database should remain consistent
    And no deadlocks should occur

  @reliability
  Scenario: Database connection recovery
    Given the database connection is temporarily lost
    When a user attempts to perform operations
    Then the system should attempt to reconnect
    And provide appropriate error messages
    And successfully reconnect when the database is available again

  @reliability
  Scenario Outline: Error handling for invalid inputs
    When I attempt to create a user with invalid "<field>" value "<value>"
    Then the operation should fail gracefully
    And an appropriate error message should be returned
    And no invalid data should be stored in the database

    Examples:
      | field    | value                    |
      | username | NULL                     |
      | username | "a"*256                  |
      | email    | "not_an_email"           |
      | is_admin | "not_a_boolean"          |
