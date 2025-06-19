Feature: Database Scalability
  As an application administrator
  I want to ensure the database scales appropriately with increased load
  So that the application can support growing user numbers

  Background:
    Given the database is initialized with test data
    And there are "100" mock users in the database

  @scalability
  Scenario Outline: Performance under growing data volume
    Given the database contains "<initial_records>" records in the "<table>" table
    When I add "<additional_records>" more records to the "<table>" table
    Then the query to retrieve all records should not slow down by more than "<max_slowdown_factor>"

    Examples:
      | initial_records | additional_records | table         | max_slowdown_factor |
      | 1000            | 9000               | users         | 5                   |
      | 5000            | 45000              | user_progress | 5                   |
      | 1000            | 9000               | user_notes    | 5                   |
      | 2000            | 18000              | quiz_results  | 5                   |

  @scalability
  Scenario: Concurrent user access scaling
    Given the database has "1000" users with progress data
    When "<num_concurrent>" users simultaneously access their progress data
    Then all requests should complete within "<max_time>" seconds
    And the system should maintain response times within "<acceptable_variance>%" variance

    Examples:
      | num_concurrent | max_time | acceptable_variance |
      | 10             | 1        | 10                  |
      | 50             | 2        | 15                  |
      | 100            | 4        | 20                  |

  @scalability
  Scenario: Database size impact on backup/restore
    Given the database contains "10000" user records
    And "50000" progress tracking entries
    And "20000" quiz result records
    When I perform a complete database backup
    Then the backup should complete within "30" seconds
    And the backup file should be successfully created
    And the database can be restored from backup within "60" seconds
