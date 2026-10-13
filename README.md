# KJEL Event Board

Trello-style board of local events for jocks and voicetrackers. One column per Type, today's events first (gold).

## Open
Double-click `index.html`. No server needed.

## Refresh (weekly)
1. `python3 scripts/collect.py` — pulls the next 60 days from 5 sources and opens every event's detail link to confirm it.
2. Add new events to `data/labels.json` (id → [Type, why line]). Events with no label stay off the board.
3. `python3 scripts/build.py` — writes `data/events.js` (the board) and `data/held_back.md` (what was dropped and why).

## Sources (all give one page per event)
Visit Lebanon · City of Lebanon calendar · Visit Pulaski County · Waynesville–St. Robert Chamber · Lake Expo

## Rules
- Every card links to that event's own page. No verified link, no card.
- Meetings, closures, chamber luncheons and towns outside the listening area are held back automatically.
- Why lines use only what the source listing says.
