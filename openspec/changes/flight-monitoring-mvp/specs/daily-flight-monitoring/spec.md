## ADDED Requirements

### Requirement: Daily scheduled execution
The system SHALL execute daily at 07:00 BRT (10:00 UTC) via GitHub Actions cron.

#### Scenario: Successful cron trigger
- **WHEN** the GitHub Actions cron triggers at 10:00 UTC
- **THEN** the daily execution workflow starts
- **AND** a new daily_execution record is created with status RUNNING

#### Scenario: Execution date uniqueness
- **WHEN** an execution is created for a date that already has a record
- **THEN** the system uses the existing record instead
- **AND** updates the started_at timestamp

### Requirement: Multi-source parallel execution
The system SHALL execute all data sources (Google Flights, Smiles, Azul, RSS) independently such that a failure in one source does not block others.

#### Scenario: One source fails, others succeed
- **WHEN** Google Flights succeeds but Smiles fails with BLOCKED status
- **THEN** Azul and RSS continue execution
- **AND** final execution status reflects partial success
- **AND** Telegram report includes all successful results and indicates failed source

#### Scenario: All sources fail
- **WHEN** all sources return error status
- **THEN** execution completes with ERROR status
- **AND** Telegram report indicates all sources unavailable
- **AND** execution record is preserved for historical tracking

### Requirement: Execution state tracking
The system SHALL track execution status for each source independently and maintain a consolidated overall execution status.

#### Scenario: Individual source status tracking
- **WHEN** a source completes (success or failure)
- **THEN** the corresponding status field (google_status, smiles_status, azul_status, rss_status) is updated
- **AND** status values are: SUCCESS, NO_AVAILABILITY, CALENDAR_NOT_OPEN, BLOCKED, TIMEOUT, PARSER_ERROR, UNKNOWN_ERROR

#### Scenario: Execution completion
- **WHEN** all sources have completed execution
- **THEN** the daily_execution status is updated to COMPLETED
- **AND** finished_at timestamp is set
- **AND** any errors are recorded in error_message field

### Requirement: Data persistence
The system SHALL persist all execution results to Supabase PostgreSQL for historical analysis.

#### Scenario: Successful quote storage
- **WHEN** a valid flight quote is obtained from any source
- **THEN** the quote is stored in daily_flight_quotes table
- **AND** includes execution_id, requested_origin, actual_origin, destination, dates, passengers
- **AND** stores price/miles data for all options found

#### Scenario: Promotion article storage
- **WHEN** a new promotional article is found
- **THEN** the article is stored in daily_promotions table
- **AND** duplicate article_url values are rejected via UNIQUE constraint
- **AND** only new articles for this execution are reported

### Requirement: Duration filtering
The system SHALL filter all flight results to exclude itineraries exceeding 30 hours total duration.

#### Scenario: Filtering applies before selection
- **WHEN** a source returns flight options with varying durations
- **THEN** only options with duration <= 30 hours are considered
- **AND** selection (lowest price/miles) is made from filtered results only

#### Scenario: No valid options within duration limit
- **WHEN** all returned options exceed 30 hours
- **THEN** source status is set to NO_AVAILABILITY
- **AND** no results are persisted for that source

### Requirement: Error state distinction
The system SHALL distinguish between technical failures and legitimate lack of availability.

#### Scenario: No availability vs error
- **WHEN** a source is successfully queried but returns no valid options
- **THEN** status is set to NO_AVAILABILITY (not ERROR)
- **AND** when source blocks/bot detection occurs
- **THEN** status is set to BLOCKED (not NO_AVAILABILITY)

### Requirement: Configuration management
The system SHALL accept trip parameters dynamically without hardcoding in scraper logic.

#### Scenario: Dynamic trip parameters
- **WHEN** the execution starts
- **THEN** scrapers receive origin (GRU/VCP), destination (BKK), dates (28/07/2027-05/08/2027), passengers (2)
- **AND** parameters are not hardcoded in scraper code
