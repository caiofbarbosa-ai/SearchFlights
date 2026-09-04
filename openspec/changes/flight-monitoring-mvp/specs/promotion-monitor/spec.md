## ADDED Requirements

### Requirement: Multi-feed RSS monitoring
The system SHALL monitor the following RSS feeds for C6 Bank and Átomos promotional content:
- Melhores Cartões
- Melhores Destinos
- Passagens Imperdíveis
- Pontos pra Voar

#### Scenario: Feed query execution
- **WHEN** the promotion monitor executes
- **THEN** it queries all four RSS feeds
- **AND** retrieves currently available articles from each

#### Scenario: Individual feed failure
- **WHEN** one feed fails to respond
- **THEN** other feeds continue processing
- **AND** the failure is logged without blocking the overall execution

### Requirement: Promotion keyword filtering
The system SHALL filter articles based on title containing C6/Átomos-related terms combined with promotional terms.

#### Scenario: Keyword matching
- **WHEN** an article title is evaluated
- **THEN** it must contain (C6 OR Átomos OR Atomos) AND (bônus OR bono OR transferência OR transferencia OR pontos)
- **AND** matching articles are flagged as relevant

#### Scenario: Term tracking
- **WHEN** an article is flagged as relevant
- **THEN** the system records which terms triggered the match
- **AND** this facilitates future filter adjustments

### Requirement: Article deduplication
The system SHALL prevent duplicate storage and notification of the same article URL.

#### Scenario: URL uniqueness
- **WHEN** an article is processed
- **THEN** the article_url is checked against existing records
- **AND** INSERT ... ON CONFLICT DO NOTHING is used
- **AND** duplicates are silently ignored

#### Scenario: Database constraint
- **WHEN** the daily_promotions table is created
- **THEN** it has a UNIQUE constraint on article_url
- **AND** this enforces deduplication at the database level

### Requirement: Promotion persistence
The system SHALL store relevant promotional articles in the daily_promotions table.

#### Scenario: Article storage
- **WHEN** a new relevant article is found
- **THEN** it is stored with: found_date, source_site, article_title, article_url
- **AND** the article_url is unique across all records

### Requirement: Repeated article handling
Articles that remain in RSS feeds for multiple days SHALL NOT generate duplicate notifications.

#### Scenario: Persistent feed article
- **WHEN** an article appears in the feed on consecutive days
- **THEN** only the first occurrence is stored
- **AND** subsequent days' executions do not create new records
- **AND** the article is not included in the "new articles" list for subsequent executions

### Requirement: No promotions state
When no relevant articles are found, the system SHALL report this state clearly without treating it as an error.

#### Scenario: No promotions found
- **WHEN** no articles match the filter criteria
- **THEN** rss_status is set to SUCCESS
- **AND** the Telegram report displays "Nenhuma promoção encontrada"
- **AND** this is not considered an execution error

### Requirement: Return only new articles
The system SHALL return only articles that are newly discovered in the current execution.

#### Scenario: New articles only
- **WHEN** the promotion monitor completes
- **THEN** it returns only articles inserted during this execution
- **AND** previously stored articles are excluded from the return list
- **AND** only new articles are included in the Telegram notification

### Requirement: Feed validation
The system SHALL validate RSS feed responses before processing.

#### Scenario: Valid feed structure
- **WHEN** an RSS feed is retrieved
- **THEN** the feed structure is validated
- **AND** required fields (title, URL) must exist
- **AND** invalid feed items are skipped with a log entry

#### Scenario: Missing required fields
- **WHEN** an article is missing title or URL
- **THEN** the article is skipped
- **AND** processing continues with remaining articles

### Requirement: Python + feedparser implementation
The system MAY use Python with the feedparser library for RSS feed processing.

#### Scenario: Feed parsing
- **WHEN** implementing RSS monitoring
- **THEN** feedparser is used to parse RSS feeds
- **AND** article data is extracted and normalized
- **AND** the filter criteria are applied to each article

### Requirement: Error isolation
Feed failures SHALL not prevent execution of other monitoring modules.

#### Scenario: All feeds fail
- **WHEN** all RSS feeds are unreachable
- **THEN** rss_status is set to an appropriate error state
- **AND** execution continues to other modules (Google Flights, Smiles, Azul)
- **AND** the Telegram report indicates RSS unavailability

### Requirement: Source site tracking
The system SHALL record which source site each promotional article came from.

#### Scenario: Source identification
- **WHEN** an article is stored
- **THEN** the source_site field identifies which feed provided it
- **AND** this enables filtering by source in future queries
