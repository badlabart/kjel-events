"""Write the board as one plain HTML file (no modern JS/CSS needed) -> docs/index.html and index.html.

Old browsers show every card from the HTML itself. A tiny ES3 script hides past
events and marks TODAY / TOMORROW; if it can't run, the board still shows.
"""
import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS = """
body{margin:0;background:#0A2A50;color:#0A2A50;font-family:Arial,Helvetica,sans-serif;font-size:15px}
.bar{background:#FDB913;padding:8px 18px;font-size:14px;color:#0A2A50}
.bar label{font-weight:bold;margin-right:8px}
.bar input{font-size:15px;padding:5px 8px;border:1px solid #0A2A50;width:180px;color:#0A2A50;background:#FFFFFF}
.bar a{color:#0A2A50;font-weight:bold;margin-left:10px}
.bar span{margin-left:12px;font-weight:bold}
.top{background:#FFFFFF;border-bottom:5px solid #FDB913;padding:10px 18px}
.logo{font-style:italic;font-weight:bold;font-size:28px;display:inline-block;vertical-align:middle;margin-right:14px}
.star{color:#FDB913;font-style:normal}.call{color:#D0101F}
.hd{display:inline-block;vertical-align:middle}
.title{font-weight:bold;font-size:16px}.meta{font-size:13px;color:#33445C}
.board{white-space:nowrap;overflow-x:auto;padding:12px 6px}
.col{display:inline-block;vertical-align:top;white-space:normal;box-sizing:border-box;width:10.3%;min-width:175px;margin:0 5px;background:#E6E9EE;border-radius:12px;padding:0 8px 4px}
.col h2{margin:0;padding:10px 4px 8px;font-size:15px}
.count{float:right;background:#D0101F;color:#FFFFFF;font-size:12px;padding:1px 8px;border-radius:10px}
.card{background:#FFFFFF;border:1px solid #C9CFD8;border-radius:8px;padding:8px 10px;margin-bottom:8px}
.card.today{background:#FFF1C2;border-color:#FDB913}
.when{font-size:12px;font-weight:bold;color:#D0101F}
.name{font-weight:bold;font-size:14px;margin:3px 0 2px}
.place{font-size:13px;color:#33445C}
.town{background:#0A2A50;color:#FFFFFF;font-size:11px;font-weight:bold;padding:1px 6px;border-radius:3px;margin-right:4px}
.why{font-size:13px;margin-top:4px}
.link{display:inline-block;margin-top:6px;font-size:12px;font-weight:bold;color:#0A2A50}
.empty{font-size:13px;color:#33445C;padding:4px 4px 10px}
"""

# ES3 only: no let/const, arrow functions, classList, or dataset.
JS = r"""
(function(){
  function p(n){return (n<10?'0':'')+n;}
  function iso(d){return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate());}
  var now=new Date(), today=iso(now), t=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1), tmr=iso(t);
  var cols=document.getElementsByTagName('div'), todayCount=0, total=0;
  for(var i=0;i<cols.length;i++){
    if(cols[i].className!=='col') continue;
    var cards=cols[i].getElementsByTagName('div'), shown=0;
    for(var j=0;j<cards.length;j++){
      var c=cards[j]; if(c.className.indexOf('card')!==0) continue;
      var d=c.getAttribute('data-date');
      if(d<today){c.style.display='none';c.setAttribute('data-past','1');continue;}
      shown++; total++;
      var w=c.getElementsByTagName('span')[0];
      var dl=c.getAttribute('data-label'), tm=c.getAttribute('data-time'), tail=(dl?' &middot; '+dl:'')+(tm?' &middot; '+tm:'');
      var keep=c.getAttribute('data-keep');
      if(d===today){c.className='card today';todayCount++; if(w && !keep) w.innerHTML='TODAY'+tail;}
      else if(d===tmr && w && !keep){w.innerHTML='TOMORROW'+tail;}
    }
    var b=cols[i].getElementsByTagName('span')[0]; if(b) b.innerHTML=shown;
  }
  var m=document.getElementById('live'); if(m) m.innerHTML=todayCount+' today &middot; '+total+' upcoming &middot; ';
  function pad2(q){return q.replace(/(^|\/)(\d)(?=\/|$)/g,'$10$2');}
  window.kjelSearch=function(){
    var q=document.getElementById('q').value.replace(/^\s+|\s+$/g,'').replace(/[-.\s]/g,'/').replace(/\/(\d\d)(\d\d)$/,'/$2');
    var qp=pad2(q), shownAll=0, divs=document.getElementsByTagName('div');
    for(var i=0;i<divs.length;i++){
      if(divs[i].className!=='col') continue;
      var cs=divs[i].getElementsByTagName('div'), n=0;
      for(var j=0;j<cs.length;j++){
        var c=cs[j]; if(c.className.indexOf('card')!==0 || c.getAttribute('data-past')) continue;
        var lb=c.getAttribute('data-label'), ok=(!q)||lb.indexOf(q)===0||lb.indexOf(qp)===0;
        c.style.display=ok?'':'none'; if(ok){n++;shownAll++;}
      }
      var b=divs[i].getElementsByTagName('span')[0]; if(b) b.innerHTML=n;
    }
    var msg=document.getElementById('msg');
    if(msg) msg.innerHTML=q?(shownAll+(shownAll===1?' event':' events')+' on dates starting '+q):'';
  };
})();
"""


def label(iso):
    y, m, d = map(int, iso.split("-"))
    return date(y, m, d).strftime("%m/%d/%y")


def write(data):
    esc = html.escape
    ev = sorted(data["events"], key=lambda e: (e["date"], e["min"]))
    cols = []
    for typ in data["types"]:
        items = [e for e in ev if e["type"] == typ]
        cards = []
        for e in items:
            when = esc(e["when"]) if e.get("when") else label(e["date"]) + (" &middot; " + esc(e["time"]) if e["time"] else "")
            place = f'<span class="town">{esc(e["town"])}</span>{esc(e["place"])}'
            link = "Details &#8599;" if e["link"] == "detail" else "On list page &#8599;"
            cards.append(
                f'<div class="card" data-date="{e["date"]}" data-label="{label(e["date"])}" data-time="{esc(e.get("time", ""))}"{' data-keep="1"' if e.get("when") else ""}>'
                f'<div class="when"><span>{when}</span></div>'
                f'<div class="name">{esc(e["title"])}</div><div class="place">{place}</div>'
                f'<div class="why">{esc(e["why"])}</div>'
                + (f'<div class="why"><b>Style:</b> {esc(e["style"])}</div>' if e.get("style") else "")
                + (f'<div class="why"><b>Attendance:</b> {esc(e["attendance"])}</div>' if e.get("attendance") else "")
                + (f'<div class="why"><b>Contact:</b> {esc(e["contact"])}</div>' if e.get("contact") else "")
                + f'<a class="link" href="{esc(e["url"])}" target="_blank" rel="noopener">{link}</a></div>')
        body = "".join(cards) or '<div class="empty">Nothing listed yet.</div>'
        cols.append(f'<div class="col"><h2>{esc(typ)} <span class="count">{len(items)}</span></h2>{body}</div>')

    updated = data["updated"].replace("T", " ")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Events</title><style>{CSS}</style></head>
<body>
<div class="bar"><label for="q">Search by date</label><input id="q" type="text" maxlength="10" onkeyup="kjelSearch()" oninput="kjelSearch()" onchange="kjelSearch()"><a href="#" onclick="document.getElementById('q').value='';kjelSearch();return false;">clear</a><span id="msg"></span></div>
<div class="top"><div class="logo">103<span class="star">&#9733;</span>7 <span class="call">KJEL</span></div>
<div class="hd"><div class="title">Events</div>
<div class="meta"><span id="live"></span>updated {esc(updated)}</div></div></div>
<div class="board">{"".join(cols)}</div>
<script>{JS}</script>
</body></html>
"""
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(page)
    (ROOT / "index.html").write_text(page)


if __name__ == "__main__":
    src = (ROOT / "data" / "events.js").read_text()
    write(json.loads(src.split("=", 1)[1].rstrip().rstrip(";")))
