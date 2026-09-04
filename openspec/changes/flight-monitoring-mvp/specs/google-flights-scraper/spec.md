## ADDED Requirements

### Requirement: Query all São Paulo airports
The system SHALL query Google Flights for GRU and VCP as origins independently and select the best result across both origins.

#### Scenario: Three origin queries
- **WHEN** the scraper executes
- **THEN** it queries GRU → BKK and VCP → BKK
- **AND** waits for response for each query
- **AND** returns the lowest price across all valid results

#### Scenario: Actual origin preservation
- **WHEN** the lowest price is found from VCP
- **THEN** both requested_origin (SAO) and actual_origin (VCP) are stored
- **AND** the report indicates the specific departure airport

### Requirement: Playwright-based scraping
The system SHALL use Playwright for browser automation and may use Playwright Stealth as an implementation detail.

#### Scenario: Direct URL navigation (primary)
- **WHEN** scraping begins
- **THEN** Playwright launches a browser
- **AND** navigates directly to the Google Flights results URL built from the textual `q=` parameter (origin, destination, dates) with pinned locale (`hl=pt-BR`, `gl=BR`, `curr=BRL`)
- **AND** waits explicitly for flight results to load

#### Scenario: Form interaction fallback
- **WHEN** the direct results URL does not render results
- **THEN** Playwright inputs origin, destination, and dates via the search form (dates typed in pt-BR format, field content verified before submission)
- **AND** passenger count is set via the passenger selector (a URL query may default to 1 adult)

#### Scenario: Response validation
- **WHEN** the page content loads
- **THEN** the scraper validates expected flight data elements exist
- **AND** extracts airline, price, duration, and itinerary details

### Requirement: Price selection for two passengers
The system SHALL return the lowest total price for 2 adults combined, not per-passenger pricing.

#### Scenario: Price calculation
- **WHEN** extracting prices from Google Flights
- **THEN** the reported price is the total for both passengers
- **AND** stored as cash_price_brl in daily_flight_quotes

### Requirement: 30-hour duration filter
The system SHALL filter results to only include itineraries with total duration <= 30 hours before selecting the lowest price.

#### Scenario: Duration filtering
- **WHEN** multiple options are available
- **THEN** options exceeding 30 hours are excluded
- **AND** lowest price is selected from remaining valid options

#### Scenario: No valid duration options
- **WHEN** all options exceed 30 hours
- **THEN** status is set to NO_AVAILABILITY
- **AND** no price data is persisted

### Requirement: Itinerary detail preservation
The system SHALL capture and store sufficient information to identify the selected flight.

#### Scenario: Minimum required data
- **WHEN** a valid option is selected
- **THEN** the following are stored: airline, origin, destination, departure_datetime, arrival_datetime, duration_minutes
- **AND** when available: flight_number, operating_airline, number_of_stops

### Requirement: Error status handling
The system SHALL report specific error states when scraping fails.

#### Scenario: Blocked access
- **WHEN** Google Flights blocks the request (CAPTCHA, 403)
- **THEN** status is set to BLOCKED
- **AND** error details are logged

#### Scenario: Timeout
- **WHEN** page load exceeds configured timeout
- **THEN** status is set to TIMEOUT
- **AND** no partial data is used

#### Scenario: Parse failure
- **WHEN** page structure has changed and expected elements are missing
- **THEN** status is set to PARSER_ERROR
- **AND** error details are logged

### Requirement: Calendar not open detection
The system SHALL identify when the queried dates are too far in advance and not yet available for booking.

#### Scenario: Future date unavailable
- **WHEN** Google Flights indicates dates are not bookable
- **THEN** status is set to CALENDAR_NOT_OPEN
- **AND** this is distinguished from NO_AVAILABILITY

### Requirement: Dynamic parameters
The scraper SHALL NOT contain hardcoded dates, airports, or passenger counts.

#### Scenario: Parameterized execution
- **WHEN** the scraper is invoked
- **THEN** it receives origin, destination, departure_date, return_date, passengers as parameters
- **AND** no trip details are hardcoded in the scraper code

### Requirement: Anti-bot detection measures
The system SHALL implement multiple measures to minimize detection as automated access.

#### Scenario: Random delays between actions
- **WHEN** the scraper interacts with the page
- **THEN** random delays are added between actions (typing, clicking, scrolling)
- **AND** delays vary between 500ms and 3000ms to simulate human behavior

#### Scenario: Human-like typing pattern
- **WHEN** entering text into form fields
- **THEN** text is typed character-by-character with random intervals
- **AND** typing speed varies to simulate human behavior

#### Scenario: Browser fingerprint obfuscation
- **WHEN** the browser is launched
- **THEN** Playwright Stealth is applied to mask automation indicators
- **AND** webdriver, chrome.runtime, and other automation flags are hidden
- **AND** browser permissions and navigator properties appear as normal browser

#### Scenario: Realistic mouse movements
- **WHEN** clicking on elements
- **THEN** mouse movements follow natural curved paths
- **AND** slight random offsets are applied to click coordinates

#### Scenario: User-agent rotation
- **WHEN** launching browser instances
- **THEN** a realistic user-agent string is used
- **AND** user-agent represents a common browser and OS combination
- **AND** user-agent may be rotated between executions if needed

#### Scenario: Request rate limiting
- **WHEN** querying multiple origins (GRU, VCP)
- **THEN** a minimum delay of 5-10 seconds is maintained between queries
- **AND** total execution time respects the source's rate limits

#### Scenario: Cookie and session persistence
- **WHEN** making multiple queries in sequence
- **THEN** browser context and cookies are maintained
- **AND** session appears as returning user rather than new session each time

#### Scenario: Headless mode considerations
- **WHEN** running in automated environment
- **THEN** headless mode is used for efficiency
- **AND** browser viewport is set to common resolution (1920x1080)
- **AND** if blocking occurs frequently, non-headless mode may be tested as alternative
