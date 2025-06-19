Feature: Database Performance
  As an application developer
  I want to ensure the database operations perform efficiently
  So that the application remains responsive under load

  Background:
    Given the database is initialized with test data
    And there are "100" mock users in the database

  @performance
  Scenario: Fast user creation
    When I create "50" new users in the database
    Then all user creation operations should complete within "1" second
    And the database should contain "150" total users

  @performance
  Scenario: Fast user retrieval
    When I retrieve all users from the database
    Then the operation should complete within "0.5" seconds
    And the data should be correctly returned

  @performance
  Scenario: Fast progress tracking
    Given there are "100" progress entries in the database
    When I add "50" new progress entries 
    Then all progress tracking operations should complete within "1" second
    And the progress retrieval for a user should complete within "0.2" seconds

  @performance
  Scenario Outline: Database query performance under varying loads
    Given the database contains "<num_records>" records in the "<table>" table
    When I execute a query to select all records from the "<table>" table
    Then the query should complete within "<max_time>" seconds

    Examples:
      | num_records | table         | max_time |
      | 1000        | users         | 0.5      |
      | 5000        | user_progress | 1.0      |
      | 1000        | user_notes    | 0.5      |
      | 2000        | quiz_results  | 0.7      |
