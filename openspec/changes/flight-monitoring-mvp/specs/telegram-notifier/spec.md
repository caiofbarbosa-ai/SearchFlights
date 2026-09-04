## ADDED Requirements

### Requirement: Consolidated daily report
The system SHALL send a single consolidated Telegram message containing all results from the daily execution.

#### Scenario: Full successful report
- **WHEN** all sources execute successfully
- **THEN** one Telegram message contains: Google Flights results, Smiles results, Azul results, and new promotions
- **AND** the message uses HTML or MarkdownV2 formatting
- **AND** special characters are properly escaped

### Requirement: Report structure and format
The Telegram message SHALL follow a consistent format with clear sections for each source.

#### Scenario: Message header
- **WHEN** the message is composed
- **THEN** it includes: "Cotação Diária: SP ↔ Bangkok", dates, passenger count
- **AND** each source has a clearly labeled section

#### Scenario: Google Flights section
- **WHEN** Google Flights has results
- **THEN** the section includes: actual origin airport, airline, total price for 2 passengers, duration
- **AND** price is formatted as currency (R$ XX.XXX,XX)

#### Scenario: Smiles section
- **WHEN** Smiles has results
- **THEN** both miles-only and Smiles & Money options are displayed
- **AND** includes: airline, mileage quantity, cash amount (if applicable), duration

#### Scenario: Azul section
- **WHEN** Azul has results
- **THEN** both points-only and Points + Money options are displayed
- **AND** includes: airline, point quantity, cash amount (if applicable), duration

#### Scenario: Promotions section
- **WHEN** new promotions are found
- **THEN** each promotion shows source site and article title
- **AND** articles are listed with bullet points

### Requirement: Unavailable source reporting
When a source is unavailable, the system SHALL clearly indicate the status in the Telegram report.

#### Scenario: Source blocked
- **WHEN** a source status is BLOCKED
- **THEN** the report indicates "Consulta indisponível hoje"
- **AND** shows the reason (e.g., "acesso bloqueado")

#### Scenario: Source no availability
- **WHEN** a source status is NO_AVAILABILITY
- **THEN** the report indicates "Nenhum voo encontrado no critério"
- **AND** this is distinguished from error states

#### Scenario: Source calendar not open
- **WHEN** a source status is CALENDAR_NOT_OPEN
- **THEN** the report indicates "Calendário ainda não aberto para estas datas"

### Requirement: No promotions message
When no promotional articles are found, the system SHALL display a specific "no promotions" message.

#### Scenario: No new promotions
- **WHEN** the promotion monitor finds no new articles
- **THEN** the report displays "📰 Promoções C6 Bank / Átomos: • Nenhuma promoção encontrada"
- **AND** this is not treated as an error condition

### Requirement: Idempotent notification
The system SHALL prevent duplicate Telegram messages for the same daily execution.

#### Scenario: Prevent duplicate sends
- **WHEN** a daily_execution already has telegram_status = SENT
- **THEN** no additional Telegram message is sent
- **AND** the system skips notification for this execution

#### Scenario: Retry mode
- **WHEN** the system is explicitly executed in retry mode
- **THEN** it may send a notification even if one was previously sent
- **AND** this is an exceptional case requiring explicit configuration

### Requirement: Telegram status tracking
The system SHALL track the notification status for each daily execution.

#### Scenario: Notification success
- **WHEN** the Telegram message is sent successfully
- **THEN** telegram_status is set to SENT
- **AND** the execution record is updated

#### Scenario: Notification failure
- **WHEN** the Telegram message fails to send
- **THEN** telegram_status is set to ERROR
- **AND** error details are logged
- **AND** the execution may be retried in a subsequent run

### Requirement: Credential security
Telegram credentials SHALL be stored as environment variables or GitHub Secrets, never in code.

#### Scenario: Credential configuration
- **WHEN** the notifier is configured
- **THEN** TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are loaded from environment
- **AND** these values are never committed to Git

### Requirement: Message formatting
The system SHALL use Telegram-compatible message formatting with proper character escaping.

#### Scenario: HTML formatting
- **WHEN** using HTML formatting mode
- **THEN** special characters (<, >, &) are properly escaped
- **AND** the message renders correctly in Telegram

#### Scenario: MarkdownV2 formatting
- **WHEN** using MarkdownV2 formatting mode
- **THEN** special characters are escaped according to Telegram's MarkdownV2 spec
- **AND** the message renders correctly in Telegram

### Requirement: Character limit compliance
The system SHALL ensure the message does not exceed Telegram's message size limit.

#### Scenario: Message within limits
- **WHEN** the report is composed
- **THEN** the total message length is under Telegram's limit (4096 characters for most message types)
- **AND** if necessary, content is condensed to fit

### Requirement: Error isolation
Telegram notification failures SHALL not prevent data persistence.

#### Scenario: Telegram fails, data saved
- **WHEN** all scrapers succeed but Telegram fails
- **THEN** all data is persisted to the database
- **AND** telegram_status is set to ERROR
- **AND** the execution can be retried later
