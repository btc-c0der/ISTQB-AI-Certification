Feature: Database Security
  As an application administrator
  I want to ensure the database operations are secure
  So that sensitive user data is protected

  Background:
    Given the database is initialized with test data
    And there are "10" regular users and "2" admin users

  @security
  Scenario: Admin privilege enforcement
    When a regular user attempts to access admin functionality
    Then the operation should be denied
    And an appropriate error message should be returned
    And the access attempt should be logged

  @security
  Scenario: SQL injection prevention
    When a user submits the following SQL injection attempts:
      | attempt                                             |
      | "admin'; --"                                        |
      | "'; DROP TABLE users; --"                           |
      | "' OR 1=1; --"                                      |
    Then all operations should fail safely
    And no unauthorized data access should occur
    And no database structure should be modified
    And the injection attempts should be logged

  @security
  Scenario: Sensitive data handling
    Given the database contains users with email addresses
    When I query the database for user information
    Then email addresses should be properly protected
    And raw password data should never be stored
    And sensitive data should be transmitted securely

  @security
  Scenario: Permission boundaries
    Given I am logged in as a regular user
    When I attempt to access another user's data
    Then the operation should be denied
    And appropriate error messages should be shown
    And the access attempt should be logged
