"""Collect upcoming events from KJEL sources, verify each detail link, write data/raw_events.json.

Run: python3 scripts/collect.py [days_ahead]
"""
import html
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw_events.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"
TODAY = date.today()
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
END = TODAY + timedelta(days=DAYS)

# Listening-area towns (Town Priority sheet + lake towns). Anything else is held back.
AREA = {
    "lebanon", "waynesville", "camdenton", "stoutland", "richland", "conway", "buffalo",
    "osage beach", "lake ozark", "laurie", "st. robert", "saint robert", "st robert",
    "fort leonard wood", "marshfield", "hermitage", "bolivar", "eldon", "dixon", "hartville",
    "versailles", "sunrise beach", "linn creek", "crocker", "climax springs", "gravois mills",
    "four seasons", "village of four seasons", "rocky mount", "macks creek", "falcon", "phillipsburg",
    "lake area", "pulaski county", "laquey", "eldridge", "plato", "brumley", "tunas", "long lane", "fair grove", "lebanon mo",
}
SKIP_WORDS = re.compile(
    r"\b(meeting|council|board|commission|committee|work session|study session|hearing|closed|"
    r"office closed|no school|deadline|luncheon|ribbon cutting|membership)\b", re.I)


def get(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data.encode() if data else None, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def text(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def ev(source, title, d, time_txt, place, town, url, desc=""):
    return {"source": source, "title": text(title), "date": d.isoformat(), "time": time_txt.strip(),
            "place": text(place), "town": text(town).title(), "url": url, "desc": text(desc)[:400]}


# ---------- Visit Lebanon (Saffire JSON service) ----------
def visit_lebanon():
    base = "https://www.visitlebanonmo.org/services/eventsservice.asmx/"
    hdr = {"Content-Type": "application/json; charset=utf-8"}
    flags = ("'categoryID':0,'tagID':0,'keywords':'','isFeatured':'false','fanPicks':'false',"
             "'pastEvents':'false','allEvents':'false','memberEvents':'false','memberOnly':'false',"
             "'showCategoryExceptionID':0,'isolatedSchedule':0,'customFieldFilters':[],'searchInDescription':false")
    body = ("{'day':'','startDate':'%s','endDate':'%s','currentUserItems':'false','myPicks':'false',%s}"
            % (TODAY.strftime("%m/%d/%Y"), END.strftime("%m/%d/%Y"), flags))
    days = json.loads(get(base + "GetEventDays", body, hdr)[1])["d"]
    out = []
    for i in range(0, len(days), 10):
        b = "{'dates':'%s','day':'',%s}" % (",".join(days[i:i + 10]), flags)
        for day in json.loads(get(base + "GetEventDaysByList", b, hdr)[1])["d"]["Days"]:
            d = datetime.strptime(day["DateString"], "%m/%d/%Y").date()
            for t in day["Times"]:
                for it in t["Items"]:
                    if it.get("IsMemberOnly") or it.get("IsPrivate") or not it.get("DetailURL"):
                        continue
                    loc = (it.get("Locations") or [{}])[0]
                    out.append(ev("Visit Lebanon", it["Name"], d, it.get("EventTimeRangeString") or "",
                                  loc.get("DisplayName") or "", loc.get("City") or "Lebanon",
                                  it["DetailURL"], it.get("ShortDescription") or ""))
    return out


# ---------- City of Lebanon (iCalendar) ----------
def city_lebanon():
    _, ics = get("https://www.lebanonmissouri.org/common/modules/iCalendar/iCalendar.aspx?catID=39&feed=calendar")
    ics = re.sub(r"\r?\n[ \t]", "", ics)
    out = []
    for blk in ics.split("BEGIN:VEVENT")[1:]:
        f = {}
        for line in blk.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f.setdefault(k.split(";")[0], v)
        m = re.search(r"(\d{8})(T(\d{4}))?", blk.split("DTSTART", 1)[1] if "DTSTART" in blk else "")
        url = re.search(r"https?://\S+EID=\d+", f.get("DESCRIPTION", ""))
        if not m or not url:
            continue
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        tm = datetime.strptime(m.group(3), "%H%M").strftime("%-I:%M %p") if m.group(3) else ""
        loc = re.sub(r"\\,", ",", f.get("LOCATION", ""))
        place = text(loc.split(" - ")[0])
        out.append(ev("City of Lebanon", f.get("SUMMARY", "").replace("\\,", ","), d, tm, place, "Lebanon", url.group(0)))
    return out


# ---------- Visit Pulaski County (all cards in page HTML) ----------
def visit_pulaski():
    page = "https://visitpulaskicounty.org/calendar-of-events/"
    _, h = get(page)
    out = []
    for a in re.finditer(r"<a href='(\?event=[^']+)' class='event-container[^>]*>(.*?)</a>", h, re.S):
        ps = [text(p) for p in re.findall(r"<p>(.*?)</p>", a.group(2), re.S)]
        name = re.search(r"<h2 class='event-name'>(.*?)</h2>", a.group(2), re.S)
        if not name or len(ps) < 2:
            continue
        try:
            d = datetime.strptime(ps[0], "%B %d, %Y").date()
        except ValueError:
            continue
        cityline = next((p for p in ps if re.search(r",\s*(Missouri|MO)\b", p, re.I)), "")
        town = cityline.split(",")[0]
        place = ps[2] if len(ps) > 2 and ps[2] != cityline else ""
        out.append(ev("Visit Pulaski County", name.group(1), d, ps[1], place, town, page + a.group(1)))
    return out


# ---------- Waynesville-St. Robert Chamber (Glue Up cards) ----------
def wsr_chamber():
    _, h = get("https://www.waynesville-strobertchamber.com/events")
    out = []
    for row in h.split('<div class="event-row">')[1:]:
        link = re.search(r'href="(https://waynesville-strobertchamber\.glueup\.com/event/\d+)"', row)
        title = re.search(r'alt="thumbnails ([^"]+)"', row)
        dt = re.search(r'<div class="event-date">\s*(\d{1,2} \w{3} \d{4})\s*\|?\s*([^<]*)</div>', row)
        venue = re.search(r'<div class="event-venue">(.*?)</div>', row, re.S)
        if not (link and title and dt):
            continue
        d = datetime.strptime(dt.group(1), "%d %b %Y").date()
        out.append(ev("Waynesville-St. Robert Chamber", title.group(1), d, dt.group(2),
                      venue.group(1) if venue else "", "Waynesville", link.group(1)))
    return out


# ---------- Lake Expo (cards; place comes from the detail page) ----------
def lake_expo():
    _, h = get("https://www.lakeexpo.com/calendar/")
    out, seen = [], set()
    for card in h.split('<div class="card-body">')[1:]:
        link = re.search(r'href="(/calendar/[^"]*event_[0-9a-f-]+\.html)"', card[:3000])
        t = text(card[:3000])
        m = re.search(r"^(.*?)\s+\w+day, (\w+ \d{1,2})\w\w, (\d{4})(?: @ ([^<]*?(?:am|pm)(?: – [^ ]+ (?:am|pm))?))?", t)
        if not (link and m) or link.group(1) in seen:
            continue
        seen.add(link.group(1))
        d = datetime.strptime(f"{m.group(2)} {m.group(3)}", "%B %d %Y").date()
        out.append(ev("Lake Expo", m.group(1), d, m.group(4) or "", "", "", "https://www.lakeexpo.com" + link.group(1)))
    return out


def lake_expo_place(e, page):
    loc = re.search(r'itemprop="location".*?itemprop="name" content="([^"]*)".*?itemprop="addressLocality" content="([^"]*)"', page, re.S)
    if loc:
        e["place"], e["town"] = text(loc.group(1)), text(loc.group(2)).title()


# ---------- verify ----------
def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", html.unescape(s).lower())


def verify(e):
    import time
    for attempt in range(3):
        try:
            status, page = get(e["url"], timeout=25)
            break
        except Exception as x:
            err = x
            time.sleep(3 * (attempt + 1))
    else:
        e["verified"], e["why_held"] = False, f"link failed: {err!r}"[:120]
        return e
    if e["source"] == "Lake Expo":
        lake_expo_place(e, page)
    words = [w for w in norm(e["title"]).split() if len(w) > 2][:4]
    body = norm(text(page))
    ok = status == 200 and words and all(w in body for w in words)
    e["verified"] = bool(ok)
    if not ok:
        e["why_held"] = "event title not found on its detail page"
    return e


def main():
    events, errors = [], {}
    for fn in (visit_lebanon, city_lebanon, visit_pulaski, wsr_chamber, lake_expo):
        try:
            got = fn()
            events += got
            print(f"{fn.__name__}: {len(got)}")
        except Exception as x:
            errors[fn.__name__] = repr(x)
            print(f"{fn.__name__}: FAILED {x!r}")

    # window, then next occurrence only per (source, title)
    events = [e for e in events if TODAY.isoformat() <= e["date"] <= END.isoformat()]
    events.sort(key=lambda e: e["date"])
    nxt = {}
    for e in events:
        nxt.setdefault((e["source"], norm(e["title"]).strip()), e)
    events = list(nxt.values())

    with ThreadPoolExecutor(4) as pool:
        events = list(pool.map(verify, events))

    for e in events:
        e["id"] = re.sub(r"\W+", "-", f'{e["source"][:4]}-{e["date"]}-{e["title"][:40]}'.lower()).strip("-")
        if e.get("verified") and SKIP_WORDS.search(e["title"]):
            e["verified"], e["why_held"] = False, "not a public event (meeting/closure/business)"
        if not e["town"]:
            e["town"] = {"Lake Expo": "Lake Area", "Visit Pulaski County": "Pulaski County"}.get(e["source"], "")
        if e.get("verified") and not e["town"]:
            e["verified"], e["why_held"] = False, "town unknown"
        if e.get("verified") and e["town"] and e["town"].lower().rstrip(".") not in AREA:
            e["verified"], e["why_held"] = False, f"outside listening area ({e['town']})"

    OUT.write_text(json.dumps({"collected": datetime.now().isoformat(timespec="minutes"),
                               "errors": errors, "events": events}, indent=1))
    ok = sum(e["verified"] for e in events)
    print(f"total {len(events)} | on board candidates {ok} | held {len(events) - ok}")


if __name__ == "__main__":
    main()
