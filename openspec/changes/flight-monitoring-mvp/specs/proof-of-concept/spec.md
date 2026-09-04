## ADDED Requirements

### Requirement: Proof of Concept phase before full implementation
The project SHALL include a POC phase to validate each scraper's technical feasibility before committing to full implementation.

#### Scenario: POC sequence
- **WHEN** the project starts
- **THEN** each scraper is validated independently as a POC
- **AND** successful POC results are documented
- **AND** only after all POCs succeed, full implementation begins

#### Scenario: POC failure handling
- **WHEN** a scraper POC demonstrates infeasibility
- **THEN** the failure is documented with root cause
- **AND** alternatives are evaluated (API, different approach, external service)
- **AND** project direction is adjusted before full implementation

#### Scenario: Alternative evaluation constraints
- **WHEN** alternatives are evaluated after a failed POC
- **THEN** only zero-cost approaches are considered (approach refinements, free tiers, execution-environment changes)
- **AND** paid commercial APIs (e.g., SerpAPI) are explicitly excluded per the R$ 0 constraint

### Requirement: Google Flights POC
The system SHALL validate Google Flights scraping feasibility with a minimal working example.

#### Scenario: Basic access validation
- **WHEN** the Google Flights POC runs
- **THEN** it successfully navigates to google.com/travel
- **AND** inputs origin (GRU), destination (BKK), and dates
- **AND** waits for flight results to load
- **AND** extracts at least one valid flight option with price and duration

#### Scenario: Multi-origin query validation
- **WHEN** the Google Flights POC queries GRU, CGH, and VCP
- **THEN** each query returns results without blocking
- **AND** total execution time completes within 5 minutes
- **AND** no CAPTCHA or blocking occurs

#### Scenario: Anti-bot measures validation
- **WHEN** the Google Flights POC runs multiple times (3+ iterations)
- **THEN** all iterations succeed without blocking
- **AND** Playwright Stealth successfully masks automation
- **AND** random delays and human-like behaviors prevent detection

#### Scenario: Data extraction validation
- **WHEN** flight results are displayed
- **THEN** the POC successfully extracts: airline name, price, duration, departure/arrival times
- **AND** validates that extracted data is accurate and parseable

### Requirement: Smiles POC
The system SHALL validate Smiles award availability scraping feasibility with a minimal working example.

#### Scenario: Basic access validation
- **WHEN** the Smiles POC runs
- **THEN** it successfully navigates to the Smiles website
- **AND** inputs origin (GRU), destination (BKK), dates, and passengers
- **AND** waits for award results to load
- **AND** extracts at least one valid award option with mileage quantity

#### Scenario: API response interception validation
- **WHEN** the Smiles POC submits a search
- **THEN** it successfully intercepts the relevant API response
- **AND** validates the JSON structure contains award data
- **AND** extracts miles-only and Smiles & Money options

#### Scenario: Multi-origin query validation
- **WHEN** the Smiles POC queries GRU, CGH, and VCP
- **THEN** each query returns results without blocking
- **AND** total execution time completes within 5 minutes
- **AND** no CAPTCHA or blocking occurs

#### Scenario: Anti-bot measures validation
- **WHEN** the Smiles POC runs multiple times (3+ iterations)
- **THEN** all iterations succeed without blocking
- **AND** Playwright Stealth and realistic behaviors prevent detection

#### Scenario: Data structure validation
- **WHEN** API responses are intercepted
- **THEN** the POC documents the JSON structure and required fields
- **AND** identifies how to extract: airline, mileage, cash amount, duration, flight details

### Requirement: Azul POC
The system SHALL validate Azul Pelo Mundo scraping feasibility with a minimal working example.

#### Scenario: Basic access validation
- **WHEN** the Azul POC runs
- **THEN** it successfully navigates to the Azul Pelo Mundo portal
- **AND** inputs origin (GRU), destination (BKK), dates, and passengers
- **AND** waits for award results to load
- **AND** extracts at least one valid award option with point quantity

#### Scenario: Portal access validation
- **WHEN** the Azul POC submits a search
- **THEN** it successfully accesses the Interline partner award section
- **AND** results display partner airline options (not just Azul flights)
- **AND** Points + Money options are visible

#### Scenario: Multi-origin query validation
- **WHEN** the Azul POC queries GRU, CGH, and VCP
- **THEN** each query returns results without blocking
- **AND** total execution time completes within 5 minutes
- **AND** no CAPTCHA or blocking occurs

#### Scenario: Anti-bot measures validation
- **WHEN** the Azul POC runs multiple times (3+ iterations)
- **THEN** all iterations succeed without blocking
- **AND** Playwright Stealth and realistic behaviors prevent detection

#### Scenario: Data extraction validation
- **WHEN** award results are displayed
- **THEN** the POC successfully extracts: airline name, point quantity, cash amount, duration, flight details
- **AND** validates that extracted data is accurate and parseable

### Requirement: POC success criteria
Each scraper POC MUST meet specific criteria to be considered successful.

#### Scenario: Success criteria
- **WHEN** evaluating a scraper POC
- **THEN** it demonstrates at least 3 successful consecutive executions
- **AND** data extraction is accurate and consistent
- **AND** no blocking or CAPTCHA occurs during testing
- **AND** execution time is acceptable (under 5 minutes per source)
- **AND** anti-bot measures prove effective

#### Scenario: Failure documentation
- **WHEN** a scraper POC fails to meet criteria
- **THEN** the failure is documented with: error type, frequency, root cause analysis
- **AND** screenshots or logs of the failure are preserved
- **AND** alternative approaches are identified

### Requirement: POC documentation
Each POC SHALL produce documentation to guide full implementation.

#### Scenario: POC report
- **WHEN** a scraper POC completes
- **THEN** a POC report is created including: working code sample, API structure documentation, anti-bot configuration, known issues, recommendations for full implementation

#### Scenario: Code reusability
- **WHEN** the POC code is reviewed
- **THEN** POC code is structured to be reusable in full implementation
- **AND** patterns established in POC are followed in production code

### Requirement: POC execution environment
POCs SHALL be executed in a simplified environment for rapid iteration.

#### Scenario: Local POC execution
- **WHEN** running scraper POCs
- **THEN** they execute locally without GitHub Actions
- **AND** use simplified configuration (environment variables or direct input)
- **AND** results are logged to console or local file

#### Scenario: POC independence
- **WHEN** POCs are developed
- **THEN** each scraper POC is independent of others
- **AND** POCs can run in any order
- **AND** failure of one POC does not block development of others

### Requirement: POC timeline gate
Full implementation SHALL NOT begin until all scraper POCs are validated.

#### Scenario: Timeline dependency
- **WHEN** planning project phases
- **THEN** POC phase is scheduled as a distinct phase with dedicated time
- **AND** main implementation phase starts only after POC sign-off
- **AND** project timeline accounts for potential POC iterations and alternative approaches

#### Scenario: Go/No-Go decision
- **WHEN** all scraper POCs complete
- **THEN** a go/no-go decision is made for each source
- **AND** only sources with successful POCs proceed to full implementation
- **AND** sources with failed POCs are either re-attempted with alternatives or excluded from MVP
