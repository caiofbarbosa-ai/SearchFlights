## ADDED Requirements

### Requirement: Smiles availability query
The system SHALL query Smiles website for award availability across GRU and VCP origins to BKK destination.

#### Scenario: Three origin queries
- **WHEN** the Smiles scraper executes
- **THEN** it queries GRU → BKK and VCP → BKK
- **AND** waits for each response to complete
- **AND** validates response structure before processing

### Requirement: Miles-only option selection
The system SHALL select the lowest total mileage option for 2 passengers with duration <= 30 hours.

#### Scenario: Miles-only selection
- **WHEN** multiple miles-only options are available
- **THEN** options exceeding 30 hours are filtered out
- **AND** the option with the lowest total mileage is selected
- **AND** stored as smiles_miles_only_qty

### Requirement: Smiles & Money option selection
The system SHALL select the option with the highest mileage value not exceeding 120,000 total miles, for 2 passengers, with duration <= 30 hours.

#### Scenario: Hybrid selection
- **WHEN** multiple Smiles & Money options are available
- **THEN** options exceeding 30 hours are filtered out
- **AND** options exceeding 120,000 total miles are filtered out
- **AND** the remaining option with the highest mileage quantity is selected
- **AND** stored as smiles_hybrid_miles_qty and smiles_hybrid_cash_brl

#### Scenario: No hybrid options under 120k miles
- **WHEN** all hybrid options exceed 120,000 miles
- **THEN** no hybrid option is selected
- **AND** the hybrid fields remain NULL for this execution

### Requirement: API response interception
The system MAY intercept the internal API response used by the Smiles website to obtain structured data.

#### Scenario: Response interception
- **WHEN** the page loads flight results
- **THEN** the scraper waits for the relevant API response
- **AND** validates the JSON structure
- **AND** normalizes the data for storage

#### Scenario: API endpoint independence
- **WHEN** implementing response interception
- **THEN** the scraper does not depend on a specific endpoint path like /gws/v1/flight/search
- **AND** implementation can adapt to endpoint changes

### Requirement: Explicit response waiting
The system SHALL wait explicitly for flight results using page.waitForResponse or equivalent, not fixed timeouts.

#### Scenario: Wait for response
- **WHEN** submitting the search form
- **THEN** the scraper waits for the flight availability response
- **AND** uses a configured timeout
- **AND** does not rely solely on waitForTimeout or networkidle

### Requirement: Response validation
The system SHALL validate the structure and content of the response before processing results.

#### Scenario: Valid response structure
- **WHEN** the response is received
- **THEN** HTTP status, JSON structure, and required fields are validated
- **AND** if invalid, status is set to PARSER_ERROR

#### Scenario: No availability in response
- **WHEN** the response is valid but contains no award options
- **THEN** status is set to NO_AVAILABILITY
- **AND** this is distinguished from parse errors

### Requirement: Two-passenger pricing
All mileage and cash values SHALL represent totals for 2 passengers, not per-passenger values.

#### Scenario: Total mileage calculation
- **WHEN** extracting mileage data
- **THEN** the stored value is the total miles for both passengers
- **AND** the stored cash value is total for both passengers

### Requirement: Error status reporting
The system SHALL report specific error states for different failure modes.

#### Scenario: Blocked access
- **WHEN** Smiles blocks the request (CAPTCHA, 403)
- **THEN** status is set to BLOCKED

#### Scenario: Timeout
- **WHEN** the response exceeds configured timeout
- **THEN** status is set to TIMEOUT

#### Scenario: Parse failure
- **WHEN** response structure is unexpected
- **THEN** status is set to PARSER_ERROR

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
- **THEN** it receives origin, destination, departure_date, return_date, passengers, cabin as parameters
- **AND** no trip details are hardcoded in the scraper code

### Requirement: Anti-bot detection measures
The system SHALL implement multiple measures to minimize detection as automated access.

#### Scenario: Random delays between actions
- **WHEN** the scraper interacts with the Smiles website
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
- **AND** total execution time respects Smiles' rate limits

#### Scenario: Session consistency
- **WHEN** making multiple searches
- **THEN** browser context and cookies are maintained
- **AND** session appears as a single user session rather than multiple connections

#### Scenario: API request simulation
- **WHEN** intercepting API responses
- **THEN** requests appear to come from legitimate browser session
- **AND** headers (Referer, Origin) match expected values from normal browsing
