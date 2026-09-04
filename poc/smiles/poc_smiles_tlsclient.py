"""
Smiles POC - Teste C: tls-client (JA3 de Chrome) + cookies do usuário.
Distingue: binding por TLS (passa aqui) vs binding por dispositivo/sensor.
Reutiliza os cookies do arquivo do Teste B (poc_smiles_api_replay.py).
"""

import sys

import tls_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, r"poc\smiles")
from poc_smiles_api_replay import HEADERS, PARAMS  # noqa: E402


def main():
    session = tls_client.Session(
        client_identifier="chrome_131",
    )
    url = ("https://api-air-flightsearch-blue.smiles.com.br/v1/airlines/search"
           "?cabin=ALL&originAirportCode=GRU&destinationAirportCode=BKK"
           "&departureDate=2026-12-08&returnDate=2026-12-16&memberNumber="
           "&adults=1&children=0&infants=0&forceCongener=false"
           "&cookies=_gid%3Dundefined%3B")
    try:
        resp = session.get(url, headers=HEADERS)
        status = resp.status_code
        body = resp.text
    except Exception as e:
        status, body = None, str(e)

    print(f"[Teste C - tls-client + cookies] status={status} bytes={len(body)}")
    print(body[:600])
    if status == 200:
        with open(r"poc\reports\smiles_api_tlsclient_success.json", "w",
                  encoding="utf-8") as f:
            f.write(body)
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
