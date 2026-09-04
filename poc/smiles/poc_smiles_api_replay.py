"""
Smiles POC - Teste B: replay com cookies do browser do usuário.
Objetivo: confirmar que o edge Akamai valida cookies de clearance no
endpoint de busca (Teste A sem cookies -> 406).
"""

import json
import sys
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW_COOKIE = (
    "_gcl_gs=2.1.k1$i1786824765$u125969807; _gcl_au=1.1.488082400.1786824772; "
    "OptanonAlertBoxClosed=2026-08-15T20:12:54.940Z; "
    "_hjSessionUser_3832769=eyJpZCI6Ijk4YmZlZjI4LTBmN2EtNWU4Zi05YTU5LTliMjdlOTg2YmEzMCIsImNyZWF0ZWQiOjE3ODY4MjQ3NzI1OTksImV4aXN0aW5nIjp0cnVlfQ==; "
    "_gcl_aw=GCL.1786824812.Cj0KCQjwnIDUBhDrARIsAJDGwSvKQQIpCx_tdBvxrbvQTp-o-agl2kAGI9TkJNXQ7ddUdwzxsQEMHboaAtggEALw_wcB; "
    "_gcl_dc=GCL.1786824812.Cj0KCQjwnIDUBhDrARIsAJDGwSvKQQIpCx_tdBvxrbvQTp-o-agl2kAGI9TkJNXQ7ddUdwzxsQEMHboaAtggEALw_wcB; "
    "_tt_enable_cookie=1; _ttp=01M03GXTZEPGH540JR73T44VMC_.tt.2; "
    "_fbp=fb.2.1786824813692.338235937783235593; __zlcmid=1Z2ojnvYO58snln; "
    "test_club_smiles=old; "
    "bm_so=B4749B9004F69D1700B9C31B80896537FA3D33BA7D91DD07005EE25A94D5C06D~YAAQhUIVAn/K1l+gAQAAnVNqYghlzBBVRx7OdD2hAhZl4KPpIVUT00vV/bC+wIcAmk2SEoaAM95hq4S04dfnJiqgrVWRWHV4FGdze7R4Zmr08THfcv9LFHidxYfB5sCaztFAvBiXv6tGVT2p4+W0Aj+N0x6Ff160xkRxwyLHHLHabLdiyfnNcfbjH4ZTkanK7s5L74RDEqhNbLYgEZoegQWfdp27F3Vahf9dCgr3Zem1S2RsJUeS6uphuDXyvbWPxE+2qIx9fDtu30KHp/86zGLX6NCQIbvJufKy0T96Tcd6qhwgLP5P+hT9JinjVYFZKdRQrrQJHxNf+l0IUi08xOeruxY+Kz3vKoTZJjjLsAZlSYvSCcJ6fq9ifnFJd7BNRcbOxVF1Q33vwJD6hLqzuYlzIN9PpYU4mmcW0j3gYLXuTamsLGYDJQODycgey//6edVRFXHRKWxp32bAj5vJrjBzw5pk; "
    "ak_bmsc=5D3DC0FCD962F9DCED9BEC9DDFECE9D7~000000000000000000000000000000~YAAQhUIVArTL1l+gAQAAklVqYgHzhytTZ4UvqjRcsXNOY3oXvgrWWz4c/QAaBdE+bWMeQy4RD5sCI2mXYfzA/ST4DpS0rAkIjlcf978lAZeFr21CzlpRUm9U8BIJJM83Jj4Sl7tnBNrFOEw4GvVKgQiOGVdu+f3Ffkd7TBQCBGOgBobiwM9FPOYj4cpjkMwIAbymsEbrmDKNHjBr/O2oaY+r3kRxVIp+ILZP3123xkl4XheSiH8uAXC8kEc88OFeBsdrZyVsSYyRhSPiQ7KvoSx1NTBkWoTW/NGUumpTNHE4DX8cbM33/So5Pow96zzrhVbJZ6Cv6ZoE6S+BtOXDdrGrlHLmK7c9HLsf2RlqwQWwm0NGdvkzHqmd02jYgGyR7K3if6szWDxXCOyDgjiUT0WDTqkH; "
    "_dd_smiles_env=blue; _clck=1k8jjup%5E2%5Eg94%5E0%5E2418; "
    "__obref=5801aca3-9e51-442a-ab6d-c7ae6e000965; "
    "_pin_unauth=dWlkPU5tSTJOekkyTWpndFlqSXlOQzAwTm1ZMkxXSTNaVFV0WVRVM1pUWTVNVEkyTURFMw; "
    "AMP_MKTG_ef9f1f5d78=JTdCJTdE; "
    "voxusmediamanager_id=17868247787210.3275714097316831rt17k99pcz; "
    "_ga=GA1.1.246755453.1788357541; "
    "voxusmediamanager_lookup_reset_count=1; measurement_id=G-BBTY3LETEV; "
    "vx_fid=01a0626a-9688-728d-bc14-426b0205308e_45.173.96.225; "
    "_uetsid=7123b330a6d611f188b99dc9a86c6cce; "
    "_uetvid=ca81582098e511f1a3d251388349f91f; fs_lua=1.1788358396131; "
    "fs_uid=#o-22R5SZ-na1#7987bbcd-6fc9-47b5-a83b-81acd29475fd:2b3be3c9-03a4-41c0-92c7-3888d6c1525b:1788357537319::2###/1818360779; "
    "ttcsid_CB46OC3C77U9V9OUJ0KG=1788357537540::2sx2Wq02p8Lcu8ufjgBJ.2.1788358396816.1; "
    "_clsk=1gxnj8s%5E1788358397660%5E2%5E1%5Ef.clarity.ms%2Fcollect; "
    "AMP_ef9f1f5d78=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjJjYjFiMDk3Yy04ZjZkLTQ2ZDYtYWNjOS0xNDY0MzJmYTRiMzAlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzg4MzU3NTM4NTA4JTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc4ODM1ODM5Nzg2OCUyQyUyMmxhc3RFdmVudElkJTIyJTNBMTUlMkMlMjJwYWdlQ291bnRlciUyMiUzQTIlMkMlMjJjb29raWVEb21haW4lMjIlM0ElMjIuc21pbGVzLmNvbS5iciUyMiU3RA==; "
    "vx_identifier=5; voxusmediamanager_ip=45.173.96.225; "
    "voxus_last_entry_before_impression=1788358406; "
    "_abck=D8871DCA60F247A7552D6EB71D9126F2~0~YAAQiioRAsPy2kWgAQAAkOZ3YhD+RXcL573DHUWqaQ6q0E8z1PMbX7rdcM0PZoK64VWmWSQlGmi2nENVmua5Fiv7HrtDlX6az33JXpXMWaJFHMqnpWmz7dSbpJZDXyOXBnEUu3pN4xDID6rPBMiWeEwZvH7gqK9tgcJ8sUVYlaHw3uPd0ffVj5ogCriH/RP9sf/91/ngjwl028pcV8DsrbpRJzDaGcsmp/+kogy1/Fsaxm5jtZxl8OFizQHQaTDDX6frdvpZo/hPA9nPvL13nMgNXrZJQ+soU/YcI4ryLuIWJzvXSGUOlWrgjdM/OCtQBejZoA5CVGdi1qB9pa0JuWpqjz6dy5USwUan7Tb2aK08+DtZrevqWcW18PoCRatiWIzoX97YEhderr1YBHcVtbIczJPSoQxZiBVbJed78Wr51vXfpb1Mk0cx6v2sTqJ01J6MwMBNHq5QMaUVh4fHDALxQu5KIGZfq7UH/Qid0QL1zUv2ZZlhGyPPIWe91W7S9AGD2LOXJmghBJDf5VtqIay7Jx4Nhq7UOEzr2isgd1VT5P6iOXowagWB5MK5/e1eom9jwRF8/lTAWIWnAQHiaFCjZcD1rLKejqyJlQ3U4jAwtkg/6xtysTURioCyAKwHzygjC2dBg6aG58ncpvjcReeCik1ooxVrx3LC9wwu/cLK484O2bozaehy+AV3SN8T7IvRokVMWYEFyL/AncO3A5xuSLlBNiD8faBcud/+kqVNXGbcxcOvMWNeZVroQ84Cc7GLT/8gTICJNi40x4f8N75IYgq3rVujcWmrLNIRHSTa5vjd1yY9z64YuVdCUzc6G6wpn8NS5MFdyFD+q7Bba0NxNtFWEhI=~-1~-1~-1~AAQAAAAG%2f%2f%2f%2f%2f9EKC1pM5BjM5T1DbDuwon467yaHSxiywm37W9flXfUgSde5yIvli%2fEJSasi+eRCtnWeVquC9Zk8dstggwhVydZiP3%2fMMFaZ42iP~-1; "
    "ttcsid=1788357537546::vOIXVxjcKFLqCqPm62YY.2.1788358396816.0::1.851681.858662::896962.4.1327.148::0.0.0; "
    "bm_s=YAAQhUIVAomC4F+gAQAAE3p8YgYIl13tMA/r4+5B2hutmy2EOZiaFPM+50ROKd7ZwgzuDlvc+rTUVpUTJAmF0V99q2DU9zUUAV0dwEaRCqk2h7iXTKZwYtNZIyk/lAcWxkkJD2qHZYLjTNJ9gKCp6J0XUceRRM6PhaItNYxi/kQhckNe//1zlmp52QmCcXLv6OxRFTt1eBxW7UwWTPQLYnhkq55AM1pCZIfSiCO/jxz6yvypLcIDGjn0oxv14sY9oRNOWUFYhlOPRJ1niiAIBCxzzGr48fM1vY6fmpwo3j33aOd4Vs1+5szgEo1voe9Nu9Pv0RGL2ZK1jIvlwMcMmL9CQrIJSDZ2IJepXtJn4NvkRXYjgqXm5lSXle8gMvCaVCghZK2g9QtxPSFyfgEDcsZaw4ionkKO9whHq8c8vL5yfWZsd+gBmDseT5ABgMRk5I4KLr/lH9b9D9qTEYkDp1dP5umh9b76GKcIE1G/tCcx4L7ra6qXxnF4cfKwc5IdnCFMAKJxPElx85ZhyoUBiCge5o+QH31VLVK7SrPSUwGp5uc5DfSfZb1OJqdrxqB85rDoAiOIuP1nQ+EFcD/VZOiYb0LWYMiSE9d9t9xWQso8mm5yhmAeJYmSyKibNyNtptHLxy9treX7NRxaTqa0UBnfgN8wLql9yI9Us1rI6msiBdR5zMiWsC27VbcTMVZrwHD4hnr3jlt+FSatqASGv0SNHnA6/qNhGWu4SYOXv2fhoEpFM5USXimiddXiaSJ0+LUyOD74gfVXt5tMnRJ6Pa0WKjRZsDd/vnR+nz/SIxDf/mMW85H44xyuvRXaXW0gmaktd00nSVveOeIAxVgyjPR8tiZpjolQfJXt8ApcnJD6qew1OcIpJeaC4Ioc3HbD+fj7zzB6teCG0H93Au3PLJSYfGnA/BSv0QdvMXHZbdWmyUOFyaEvEL0Ae2rNY5d3OZMwvXgD0hejaOoauhPQLDINIdddaU9xM9Hexn9MrukHC1H5wo8rs7V8P2yy+IqEnCRUKVrWpcssgB/rXk6UzlFBtLZ2hgmAQWCXFhAJF5Jv07t51RkGoUhlFUfXX2bJ1rbNFC8AkJd09+oKieT0QqBAz8qCsg8DG5; "
    "bm_sz=08DC8B7D4E6A69F6421257F572E74CDC~YAAQhUIVAoqC4F+gAQAAE3p8YgGaqgT2nyEBUPoNcD/0wrTm8n4x4C+/XNgAV6hDKbZhFbvpzf243xCCLwbwW38PAHbmrwwIsM9v4MitPNrKRe0pM2ceKlQ4ePTA1SwXID7whMkg/RVO5xFQ8lPBUatPJK9qc2WPM22+CgyYFXlFXktSIztFqoQSIx/lC+n4blDLcDJOluRSPFb6AInbbrwvPm3GOfByuD2ehi1N8LJ3d6fiRx/6oeowrVKFcefeV6ysttlB1BmsVfoAzSyspnDv/Jcq/JQyJJVwmqAGYCcWi0iFM/2EXYdy443A+MMzeWHvn9Jcb2IzBjy2CeUebXTyS14WHwYeIelbVAP4ItXQZkRh7CqL0kDynHGQs+6OJWAYeDfhg5wBf/DeHk1M9eYE+SIGkMrMq+R/ALySL54NyZS9NfKHxdHCNCAC~3421496~3360070; "
    "_dd_s=aid=0575cce9-c4d7-4ea0-a77e-c0c0ac171d3c&rum=2&id=6a203887-bf01-4364-8db1-9ac0d548588a&created=1788357532561&expire=1788359619734; "
    "OptanonConsent=isGpcEnabled=0&datestamp=Wed+Sep+02+2026+11%3A18%3A40+GMT-0300+(GMT-03%3A00)&version=202606.1.0&browserGpcFlag=0&isDntEnabled=0&isIABGlobal=false&hosts=&consentId=a8a263f5-e17f-4008-841f-68e52c152dbc&interactionCount=1&isAnonUser=1&prevHadToken=0&landingPath=NotLandingPage&groups=C0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0001%3A1&fclco=&lastConsentTs=1786824775&intType=1&crTime=1786824775674&geolocation=BR%3BSP&AwaitingReconsent=false; "
    "_ga_BBTY3LETEV=GS2.1.s1788357541$o1$g1$t1788358723$j14$l0$h0; "
    "_ga_L25DPPG37X=GS2.1.s1788357541$o1$g1$t1788358724$j13$l0$h2038524373; "
    "bm_sv=066C2E0F09882374C295A6DE792A27E3~YAAQhUIVAsqL4F+gAQAAAo58YgGohPCse21B8yJCGqCuvuJXTEj6gBUbSNeU+0PwaNG3w96YRcgDcuSpKZN++hsALHMM7hIQPKnIzt0/J3K9E/c/VAtQg9HGypEIHpixauexjMXAZltLVdhYpHVjCIaNta9wi3l63eaDFE8Zm2W9L0OVz3aAReoJ5idrgiahQtO6Vi+WWfkTNrBsQ7p+viwk3mtuowRlRlxiwyjGG/Ne66CT6X/88IHrBsdqqETQa7rkiw==~1"
)

PARAMS = {
    "cabin": "ALL", "originAirportCode": "GRU", "destinationAirportCode": "BKK",
    "departureDate": "2026-12-08", "returnDate": "2026-12-16",
    "memberNumber": "", "adults": "1", "children": "0", "infants": "0",
    "forceCongener": "false", "cookies": "_gid=undefined;",
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "channel": "WEB",
    "origin": "https://www.smiles.com.br",
    "referer": "https://www.smiles.com.br/",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/151.0.0.0 Safari/537.36"),
    "x-api-key": "aJqPU7xNHl9qN3NVZnPaJ208aPo2Bh2p2ZV844tw",
    "cookie": RAW_COOKIE,
}


def main():
    url = ("https://api-air-flightsearch-blue.smiles.com.br/v1/airlines/search?"
           + urllib.parse.urlencode(PARAMS))
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        status, body = None, str(e)

    print(f"[Teste B - replay c/ cookies] status={status} bytes={len(body)}")
    print(body[:600])
    if status == 200:
        with open(r"poc\reports\smiles_api_airlines_search_success.json", "w",
                  encoding="utf-8") as f:
            f.write(body)
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                print(f"\n[chaves] {list(data.keys())[:15]}")
            else:
                print(f"\n[lista] {len(data)} itens")
                print(json.dumps(data[0], ensure_ascii=False, indent=2)[:1200])
        except Exception as e:
            print(f"parse: {e}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
