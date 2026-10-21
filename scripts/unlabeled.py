"""Print verified events that have no label yet (one line each), for the daily refresh.
Skipped events carry a ["SKIP", reason] label so they are not printed again."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
raw = json.loads((ROOT / "data" / "raw_events.json").read_text())
labels = json.loads((ROOT / "data" / "labels.json").read_text())

new = [e for e in raw["events"] if e.get("verified") and e["id"] not in labels]
for e in new:
    print(" | ".join([e["id"], e["title"][:80], e["place"][:40], e["town"], e["desc"][:160]]))
print(f"{len(new)} unlabeled")
