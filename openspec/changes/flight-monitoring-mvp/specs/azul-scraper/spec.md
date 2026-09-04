## ADDED Requirements

### Requirement: Azul Pelo Mundo availability query
The system SHALL query the Azul Pelo Mundo / Interline portal for award availability across GRU and VCP origins to BKK destination.

#### Scenario: Three origin queries
- **WHEN** the Azul scraper executes
- **THEN** it queries GRU → BKK and VCP → BKK
- **AND** waits for each response to complete
- **AND** validates response structure before processing

### Requirement: Points-only option selection
The system SHALL select the lowest total point quantity option for 2 passengers with duration <= 30 hours.

#### Scenario: Points-only selection
- **WHEN** multiple points-only options are available
- **THEN** options exceeding 30 hours are filtered out
- **AND** the option with the lowest total point quantity is selected
- **AND** stored as azul_miles_only_qty

### Requirement: Points + Money option selection
The system SHALL select the option with the highest point value not exceeding 120,000 total points, for 2 passengers, with duration <= 30 hours.

#### Scenario: Hybrid selection
- **WHEN** multiple Points + Money options are available
- **THEN** options exceeding 30 hours are filtered out
- **AND** options exceeding 120,000 total points are filtered out
- **AND** the remaining option with the highest point quantity is selected
- **AND** stored as azul_hybrid_miles_qty and azul_hybrid_cash_brl

#### Scenario: No hybrid options under 120k points
- **WHEN** all hybrid options exceed 120,000 points
- **THEN** no hybrid option is selected
- **AND** the hybrid fields remain NULL for this execution

### Requirement: Playwright-based portal access
The system SHALL use Playwright to navigate the Azul portal and extract award availability data.

#### Scenario: Portal navigation
- **WHEN** scraping begins
- **THEN** Playwright launches a browser
- **AND** navigates to the Azul Pelo Mundo portal
- **AND** inputs origin, destination, dates, and passenger count
- **AND** waits explicitly for results to load

#### Scenario: Response validation
- **WHEN** the results load
- **THEN** the scraper validates expected award data elements exist
- **AND** extracts airline, points, cash, duration, and itinerary details

### Requirement: Explicit waiting for results
The system SHALL wait explicitly for award results to load, not using fixed timeouts as the primary mechanism.

#### Scenario: Wait for results
- **WHEN** submitting the search form
- **THEN** the scraper waits for the award results to be displayed
- **AND** uses a configured timeout
- **AND** does not rely solely on waitForTimeout or networkidle

### Requirement: Response validation
The system SHALL validate the structure and content of the results before processing.

#### Scenario: Valid result structure
- **WHEN** the results are displayed
- **THEN** the page structure and required data fields are validated
- **AND** if invalid, status is set to PARSER_ERROR

#### Scenario: No availability in results
- **WHEN** the portal loads but shows no award options
- **THEN** status is set to NO_AVAILABILITY
- **AND** this is distinguished from parse errors

### Requirement: Two-passenger pricing
All point and cash values SHALL represent totals for 2 passengers, not per-passenger values.

#### Scenario: Total point calculation
- **WHEN** extracting point data
- **THEN** the stored value is the total points for both passengers
- **AND** the stored cash value is total for both passengers

### Requirement: Error status reporting
The system SHALL report specific error states for different failure modes.

#### Scenario: Blocked access
- **WHEN** Azul blocks the request (CAPTCHA, 403)
- **THEN** status is set to BLOCKED

#### Scenario: Timeout
- **WHEN** the response exceeds configured timeout
- **THEN** status is set to TIMEOUT

#### Scenario: Parse failure
- **WHEN** result structure is unexpected
- **THEN** status is set to PARSER_ERROR

### Requirement: Calendar not open detection
The system SHALL identify when the queried dates are not yet available for award booking.

#### Scenario: Future date unavailable
- **WHEN** Azul indicates dates are not bookable
- **THEN** status is set to CALENDAR_NOT_OPEN
- **AND** this is distinguished from NO_AVAILABILITY

### Requirement: Itinerary detail preservation
The system SHALL store sufficient information to identify the selected award itinerary.

#### Scenario: Required data fields
- **WHEN** a valid option is selected
- **THEN** the following are stored: airline, origin, destination, departure_datetime, arrival_datetime, duration_minutes
- **AND** when available: flight_number, operating_airline, number_of_stops

### Requirement: Dynamic parameters
The scraper SHALL accept trip parameters dynamically without hardcoding.

#### Scenario: Parameterized execution
- **WHEN** the scraper is invoked
- **THEN** it receives origin, destination, departure_date, return_date, passengers as parameters
- **AND** no trip details are hardcoded in the scraper code

### Requirement: Playwright Stealth as implementation detail
The use of Playwright Stealth is an implementation detail and not a functional requirement.

#### Scenario: Stealth independence
- **WHEN** the scraper is implemented
- **THEN** Playwright Stealth may be used as an anti-detection measure
- **AND** removal or replacement of Stealth does not constitute a functional change

### Requirement: Anti-bot detection measures
The system SHALL implement multiple measures to minimize detection as automated access.

#### Scenario: Random delays between actions
- **WHEN** the scraper interacts with the Azul portal
- **THEN** random delays are added between actions (typing, clicking, scrolling)
- **AND** delays vary between 500ms and 3000ms to simulate human behavior

#### Scenario: Human-like typing pattern
- **WHEN** entering search parameters into form fields
- **THEN** text is typed character-by-character with random intervals
- **AND** typing speed varies to simulate human behavior

#### Scenario: Browser fingerprint obfuscation
- **WHEN** the browser is launched
- **THEN** Playwright Stealth is applied to mask automation indicators
- **AND** webdriver, chrome.runtime, and other automation flags are hidden
- **AND** browser permissions and navigator properties appear as normal browser

#### Scenario: Realistic mouse movements
- **WHEN** clicking on elements or buttons
- **THEN** mouse movements follow natural curved paths
- **AND** slight random offsets are applied to click coordinates

#### Scenario: Request rate limiting
- **WHEN** querying multiple origins (GRU, VCP)
- **THEN** a minimum delay of 5-10 seconds is maintained between queries
- **AND** total execution time respects Azul's rate limits

#### Scenario: Session consistency
- **WHEN** making multiple searches
- **THEN** browser context and cookies are maintained
- **AND** session appears as a single user session rather than multiple connections

#### Scenario: Portal-specific headers
- **WHEN** accessing the Azul Pelo Mundo portal
- **THEN** request headers match expected values from normal browser navigation
- **AND** Referer and Origin headers are properly set
