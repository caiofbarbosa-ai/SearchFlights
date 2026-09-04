"""
Smiles POC - API direta v2 (2026-09-02, com cURL de referência do usuário)
Descobertas do cURL: auth por x-api-key (não Bearer!), datas ISO, param
forceCongener, param "cookies" estranho. Teste A: sem cookies (browserless).
"""

import json
import sys
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_KEY = "SMILES_X_API_KEY_REDACTED"
BASE = "https://api-air-flightsearch-blue.smiles.com.br"

PARAMS = {
    "cabin": "ALL",
    "originAirportCode": "GRU",
    "destinationAirportCode": "BKK",
    "departureDate": "2026-12-08",
    "returnDate": "2026-12-16",
    "memberNumber": "",
    "adults": "1",
    "children": "0",
    "infants": "0",
    "forceCongener": "false",
    "cookies": "_gid=undefined;",
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "pt-BR,pt;q=0.9",
    "channel": "WEB",
    "origin": "https://www.smiles.com.br",
    "referer": "https://www.smiles.com.br/",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/151.0.0.0 Safari/537.36"),
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "x-api-key": API_KEY,
}


def get(url: str, headers: dict) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def main():
    url = f"{BASE}/v1/airlines/search?{urllib.parse.urlencode(PARAMS)}"
    print(f"GET {url[:120]}...")

    # Teste A: SEM cookies (browserless puro)
    status, body = get(url, HEADERS)
    print(f"\n[Teste A - sem cookies] status={status} bytes={len(body)}")
    print(f"body (primeiros 800):\n{body[:800]}")

    with open(r"poc\reports\smiles_api_direct_v2_testA.json", "w",
              encoding="utf-8") as f:
        f.write(body if status == 200 else f"status={status}\n{body}")

    if status == 200:
        try:
            data = json.loads(body)
            print(f"\n[estrutura] tipo: {type(data).__name__}")
            if isinstance(data, list):
                print(f"  {len(data)} itens; primeiro item:")
                print(json.dumps(data[0], ensure_ascii=False, indent=2)[:1500])
            elif isinstance(data, dict):
                print(f"  chaves: {list(data.keys())[:15]}")
        except Exception as e:
            print(f"  JSON inválido: {e}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
