"""Merge verified events with labels -> data/events.js (board data) and data/held_back.md.

Run after collect.py and after labels.json is updated.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = ["Holiday Events", "KIM ONLY", "Manual Entries", "Family", "Community and Causes", "Outdoors and Lake",
         "School and Sports", "Date Night", "Girls Night", "Live Music"]

def clean_time(t):
    t = re.sub(r"\s*(am|pm)\b", lambda m: " " + m.group(1).upper(), t.strip(), flags=re.I)
    t = re.sub(r"\s*[-–]\s*", " – ", t)
    t = re.sub(r"\b0(\d:)", r"\1", t)
    return "" if t.startswith(("12:00 AM – 12:00 AM", "12:00 AM – 11:59 PM")) else t


def minutes(t):
    m = re.match(r"(\d{1,2}):(\d\d) (AM|PM)", t)
    if not m:
        return -1
    h = int(m.group(1)) % 12 + (12 if m.group(3) == "PM" else 0)
    return h * 60 + int(m.group(2))


TOWN_FIX = {"St. Robert": "Saint Robert", "St Robert": "Saint Robert", "Eldridge.": "Eldridge"}


raw = json.loads((ROOT / "data" / "raw_events.json").read_text())
labels = json.loads((ROOT / "data" / "labels.json").read_text())

# Inside the 7-day window every occurrence of a recurring event is kept, so a later date of an event
# that already has a label reuses it. MaxPreps games are labeled by the script (Boss 2026-10-21).
same_title = {}
for e in raw["events"]:
    if e["id"] in labels:
        same_title.setdefault((e["source"], e["title"].lower()), labels[e["id"]])

board, held = [], []
for e in raw["events"]:
    lab = labels.get(e["id"]) or same_title.get((e["source"], e["title"].lower()))
    if not lab and e["source"] == "MaxPreps":
        lab = ["School and Sports", e["why"]]
    if not e.get("verified"):
        held.append((e, e.get("why_held", "not verified")))
    elif not lab:
        held.append((e, "not picked for the board"))
    elif lab[0] == "SKIP":
        held.append((e, "skipped: " + lab[1]))
    elif lab[0] not in TYPES:
        held.append((e, f"unknown Type {lab[0]!r}"))
    else:
        t = clean_time(e["time"])
        board.append({"title": e["title"], "date": e["date"], "time": t, "min": minutes(t), "place": e["place"],
                      "town": TOWN_FIX.get(e["town"], e["town"]), "url": e["url"], "link": "detail", "type": lab[0], "why": lab[1], "style": lab[2] if len(lab) > 2 else "",
                      "source": e["source"]})

data = {"updated": raw["collected"], "types": TYPES, "events": board}
(ROOT / "data" / "events.js").write_text("window.KJEL_EVENTS = " + json.dumps(data, ensure_ascii=False) + ";\n")

lines = [f"# Held back — {raw['collected']}", "", f"{len(held)} events not on the board.", ""]
for e, why in sorted(held, key=lambda x: (x[1], x[0]["date"])):
    lines.append(f"- {e['date']} · {e['title']} · {e['town'] or '?'} · {why} · {e['url']}")
(ROOT / "data" / "held_back.md").write_text("\n".join(lines) + "\n")
print(f"board {len(board)} | held {len(held)}")

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
import page  # noqa: E402
meetups = json.loads((ROOT / "data" / "meetups.json").read_text())["meetups"]
manual = json.loads((ROOT / "data" / "manual.json").read_text())["entries"]
page_data = dict(data, events=data["events"] + [dict(m, type="KIM ONLY", style="", source="Meetups") for m in meetups]
                 + [dict(m, type="Manual Entries", style="", source="Manual") for m in manual])
page.write(page_data)
print("page written: docs/index.html")
