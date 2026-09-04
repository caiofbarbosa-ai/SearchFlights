"""
Smiles POC - Teste de API direta (sem browser, sem login)
O site cunha token client-credentials com credenciais públicas do próprio
config (visível no LaunchDarkly). Teste: o endpoint de flightsearch aceita?

Observação: credenciais client_id/client_secret são públicas (embutidas no
JS do portal smiles.com.br) — não são credenciais de usuário.
"""

import json
import sys

import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLIENT_ID = "2gpRUWTOBFgi2uypotR3gBUhCtVuYs2G"
CLIENT_SECRET = "U2_qer1iuZBhdIS7IlUXlvkdesl98Yjv38OmW5eu__XlXz-3aWLhAFPVNcig3V3e"
AUDIENCE = "https://smiles.api"

TOKEN_URL = "https://apigw-blue.smiles.com.br/b2b/partner/oauth/token/"
SEARCH_HOST = "https://api-air-flightsearch-blue.smiles.com.br"

DEP_MS = 1796698800000  # 2026-12-08 00:00 BRT
RET_MS = 1797433200000  # 2026-12-16 00:00 BRT


def http(method: str, url: str, headers: dict = None, body: dict = None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    req.add_header("Origin", "https://www.smiles.com.br")
    req.add_header("Referer", "https://www.smiles.com.br/")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def main():
    # 1. token client-credentials
    status, body = http("POST", TOKEN_URL, body={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "audience": AUDIENCE, "grant_type": "client_credentials",
    })
    print(f"[token] status={status}")
    token = None
    try:
        data = json.loads(body)
        token = data.get("access_token")
        print(f"[token] access_token: {'OK (' + str(len(token)) + ' chars)' if token else 'AUSENTE'}")
        print(f"[token] campos: {list(data.keys())[:8]}")
    except Exception:
        print(f"[token] body (primeiros 300): {body[:300]}")

    if not token:
        print(">>> sem token; API direta inviável neste caminho")
        return 1

    auth = {"Authorization": f"Bearer {token}"}

    # 2. endpoints de busca — o que o browser tentou + variantes plausíveis
    candidates = [
        f"/v1/airlines/search?cabin=ALL&originAirportCode=GRU"
        f"&destinationAirportCode=BKK&departureDate={DEP_MS}"
        f"&returnDate={RET_MS}&adults=1&children=0&infants=0&tripType=1",
        f"/v1/airlines/search?cabin=ALL&originAirportCode=GRU"
        f"&destinationAirportCode=BKK&departureDate={DEP_MS}"
        f"&returnDate={RET_MS}&adults=1&tripType=1&searchType=congenere",
        f"/v1/flights/search?cabin=ALL&originAirportCode=GRU"
        f"&destinationAirportCode=BKK&departureDate={DEP_MS}"
        f"&returnDate={RET_MS}&adults=1&tripType=1",
    ]
    results = []
    for path in candidates:
        status, body = http("GET", SEARCH_HOST + path, headers=auth)
        print(f"\n[search] {path[:90]}...")
        print(f"         status={status} | bytes={len(body)}")
        print(f"         body: {body[:300]}")
        results.append({"path": path, "status": status, "body": body[:2000]})

    with open(r"poc\reports\smiles_api_direct_test.json", "w",
              encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
