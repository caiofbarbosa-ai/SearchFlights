# Flight Monitoring MVP - Proof of Concept

## Objective

Validate technical feasibility of each scraper before full implementation.

## Structure

```
poc/
├── google_flights/     # Google Flights POC
├── smiles/            # Smiles POC
├── azul/              # Azul POC
├── reports/           # POC findings and reports
└── requirements-poc.txt
```

## Success Criteria

Each POC must demonstrate:
- ✅ 3+ consecutive successful executions
- ✅ No blocking or CAPTCHA during testing
- ✅ Accurate data extraction
- ✅ Execution time under 5 minutes per source
- ✅ Anti-bot measures prove effective

## Running POCs

```bash
# Install dependencies
pip install -r requirements-poc.txt
playwright install chromium

# Run individual POCs
python google_flights/poc.py
python smiles/poc.py
python azul/poc.py
```

## Parameters

- Origin: GRU, CGH, VCP (São Paulo airports)
- Destination: BKK (Bangkok)
- Departure: 2027-07-28
- Return: 2027-08-05
- Passengers: 2 adults
- Max Duration: 30 hours
