"""
Azul POC - Teste de API direta (browserless)
/api/availability responde para Python puro? (decide arquitetura do Azul)
"""

import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    # URL completa capturada no flow (hits salvos)
    hits = json.load(open(r"poc\reports\azul_flow_api_hits.json",
                          encoding="utf-8"))
    full_url = None
    for h in hits:
        if "availability" in h["url"]:
            full_url = h["url"]
            break
    print(f"URL capturada: {full_url}")
    if not full_url:
        print("[FAIL] URL de availability não encontrada nos hits")
        return 1

    req = urllib.request.Request(full_url, method="GET")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/151.0.0.0 Safari/537.36"))
    req.add_header("Referer", "https://azulpelomundo.voeazul.com.br/")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        status, body = None, str(e)

    print(f"[API direta Python] status={status} bytes={len(body)}")
    print(body[:400])
    if status == 200:
        with open(r"poc\reports\azul_api_direct_success.json", "w",
                  encoding="utf-8") as f:
            f.write(body)
        data = json.loads(body)
        s = json.dumps(data, ensure_ascii=False)
        print("\n[estrutura] chaves:", list(data.keys())[:10])
        for airline in ("Qatar", "Emirates", "Turkish", "JAL", "Japan",
                        "KLM", "AirFrance", "Air France", "Swiss",
                        "Ethiopian", "United"):
            c = s.count(airline)
            if c:
                print(f"  {airline}: {c} menções")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
