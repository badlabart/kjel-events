"""Merge verified events with labels -> data/events.js (board data) and data/held_back.md.

Run after collect.py and after labels.json is updated.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = ["Date Night", "Girls Night", "Family", "Live Music", "School and Sports",
         "Community and Causes", "Outdoors and Lake", "Holiday Events"]

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


raw = json.loads((ROOT / "data" / "raw_events.json").read_text())
labels = json.loads((ROOT / "data" / "labels.json").read_text())

board, held = [], []
for e in raw["events"]:
    lab = labels.get(e["id"])
    if not e.get("verified"):
        held.append((e, e.get("why_held", "not verified")))
    elif not lab:
        held.append((e, "not picked for the board"))
    elif lab[0] not in TYPES:
        held.append((e, f"unknown Type {lab[0]!r}"))
    else:
        t = clean_time(e["time"])
        board.append({"title": e["title"], "date": e["date"], "time": t, "min": minutes(t), "place": e["place"],
                      "town": e["town"], "url": e["url"], "link": "detail", "type": lab[0], "why": lab[1],
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
page.write(data)
print("page written: docs/index.html")
