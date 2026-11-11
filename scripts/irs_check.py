"""Look up whether an event host is a 501(c)(3), using ProPublica Nonprofit Explorer (IRS Business Master File data).

Boss (2026-11-11): Show Prep events must be non-commercial. The host must be a 501(c)(3) or a government body
(school, library, city, county, state, Fort Leonard Wood). No raffles, bingo, silent auctions or other games of chance.

Usage: python3 -I scripts/irs_check.py "Lions Club Fort Leonard Wood" ["Another host" ...]
Prints up to 5 Missouri matches per name: subsection (3 = 501(c)(3)), name, city, EIN.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://projects.propublica.org/nonprofits/api/v2/search.json?"


def search(name, state="MO"):
    url = API + urllib.parse.urlencode({"q": name, "state[id]": state})
    req = urllib.request.Request(url, headers={"User-Agent": "kjel-showprep/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("organizations", [])
    except Exception as ex:  # 404 = no match on ProPublica
        return [] if "404" in str(ex) else [{"name": f"LOOKUP FAILED: {ex}"}]


if __name__ == "__main__":
    for i, n in enumerate(sys.argv[1:]):
        if i:
            time.sleep(1)
        orgs = search(n)
        print(f"== {n}: {len(orgs)} match(es)")
        for o in orgs[:5]:
            print(f"   c({o.get('subseccd', '?')}) | {o.get('name')} | {o.get('city', '')} | EIN {o.get('ein', '')}")
