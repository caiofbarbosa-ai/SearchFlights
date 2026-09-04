"""Probe: descobrir e validar feeds RSS das fontes de notícias."""

import feedparser

CANDIDATES = [
    ("melhoresdestinos", [
        "https://www.melhoresdestinos.com.br/feed",
        "https://www.melhoresdestinos.com.br/feed/",
    ]),
    ("melhorescartoes", [
        "https://www.melhorescartoes.com.br/feed",
        "https://melhorescartoes.com.br/feed",
    ]),
    ("passageirodeprimeira", [
        "https://passageirodeprimeira.com/feed",
        "https://www.passageirodeprimeira.com/feed",
    ]),
    ("pontospravoar", [
        "https://www.pontospravoar.com/feed",
        "https://pontospravoar.com/feed",
    ]),
    ("smiles", [
        "https://www.smiles.com.br/rss",
        "https://www.smiles.com.br/feed",
        "https://blog.smiles.com.br/feed",
    ]),
]


def log(m):
    print(m, flush=True)


def main():
    working = {}
    for name, urls in CANDIDATES:
        found = None
        for url in urls:
            try:
                feed = feedparser.parse(url)
                entries = getattr(feed, "entries", [])
                title = (getattr(feed.feed, "title", "") or "").strip()
                if entries and (title or getattr(feed, "version", "")):
                    found = (url, len(entries), title,
                             entries[0].get("title", "")[:70])
                    break
                status = getattr(feed, "status", "?")
                log(f"  [{name}] {url} -> sem entradas (status {status}, "
                    f"bozo={feed.bozo})")
            except Exception as e:
                log(f"  [{name}] {url} -> ERRO {str(e)[:80]}")
        if found:
            url, n, title, latest = found
            log(f"✅ {name}: {url} | {n} entradas | feed: {title!r}")
            log(f"   mais recente: {latest!r}")
            working[name] = url
        else:
            log(f"❌ {name}: nenhum feed funcionou")

    print("\nFEEDS FUNCIONAIS:")
    for name, url in working.items():
        print(f"  {name}: {url}")


if __name__ == "__main__":
    main()
