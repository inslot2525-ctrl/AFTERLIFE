"""/partner: a pretend partner site that embeds Shelf's widget, for the resurrection demo.

It calls /embed/widget only when someone clicks the button, never on page load,
so a visitor can't knock by accident. During embed_widget's vigil one click is
a knock: the flag comes back on and the retirement is called off.

Not a feature: it has no flag and the census never counts it.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.graveyard import STYLE, nav

# The partner's key, sent as x-partner-key; the knock log shows it as the caller.
# scripts/traffic.py --partner uses the same key.
PARTNER_KEY = "acme-quarterly-report"

router = APIRouter()

PAGE_STYLE = """
.demo-note { background: var(--card); border: 1px dashed var(--line); border-radius: 10px; padding: 10px 14px;
  color: var(--quiet); font-size: 13.5px; margin: 0 0 20px; }
.partner { background: #fff8ee; color: #2b2116; border-radius: 14px; padding: 22px 24px; max-width: 640px;
  box-shadow: 0 1px 0 rgba(0,0,0,.06); }
.partner h2 { font: 700 22px/1.2 Georgia, "Times New Roman", serif; margin: 0 0 4px; color: #2b2116; }
.partner .tag { color: #7a6650; margin: 0 0 18px; font-size: 14px; }
.partner button { background: #b5532a; color: #fff; border: 0; border-radius: 8px; padding: 10px 16px;
  font: 600 15px system-ui, sans-serif; cursor: pointer; }
.partner button:disabled { opacity: .6; cursor: wait; }
.slot { margin-top: 16px; min-height: 64px; border: 1px solid #ead8c3; border-radius: 10px; padding: 12px 14px;
  background: #fff; }
.slot .shelf-widget ul { margin: 6px 0 0 18px; padding: 0; }
.slot.retired { border-color: #d4493b; color: #8f2a20; }
.slot.empty { color: #7a6650; }
.log { margin-top: 18px; font: 12.5px/1.6 ui-monospace, Consolas, monospace; color: var(--quiet); }
.log b { color: var(--ink); }
"""

SCRIPT = f"""<script>
(function () {{
  var button = document.getElementById('load'), slot = document.getElementById('slot'), log = document.getElementById('log');
  function note(status, text) {{
    var row = document.createElement('div');
    var when = new Date().toISOString().slice(11, 19) + ' UTC';
    row.innerHTML = '<b>' + when + '</b> GET /embed/widget &rarr; ' + status + ' ' + text;
    log.prepend(row);
  }}
  button.addEventListener('click', function () {{
    button.disabled = true;
    fetch('/embed/widget', {{headers: {{'x-partner-key': '{PARTNER_KEY}'}}, cache: 'no-store'}})
      .then(function (r) {{
        return r.text().then(function (body) {{
          if (r.ok) {{
            slot.className = 'slot'; slot.innerHTML = body; note(r.status, 'widget shown');
          }} else if (r.status === 410) {{
            slot.className = 'slot retired';
            slot.textContent = 'Shelf has switched this widget off while it decides whether to retire it. '
              + 'Our request was logged as a knock, so it should come back.';
            note(r.status, 'retired, knock logged');
          }} else {{
            slot.className = 'slot retired';
            slot.textContent = r.status === 404 ? 'Shelf has retired this widget for good.' : 'Shelf answered ' + r.status + '.';
            note(r.status, r.status === 404 ? 'gone' : 'error');
          }}
        }});
      }})
      .catch(function () {{ note('-', 'network error'); }})
      .finally(function () {{ button.disabled = false; }});
  }});
}})();
</script>"""


def render() -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Partner demo</title><style>{STYLE}{PAGE_STYLE}</style></head><body><main>"
        + nav("Partner demo")
        + "<h1>Partner demo</h1>"
        "<p class='demo-note'>A pretend partner site, Acme Book Club, that embeds Shelf's "
        "&ldquo;currently reading&rdquo; widget. Acme is made up for the demo. The button sends one real "
        "request to <code>/embed/widget</code> with Acme's partner key, and nothing is sent until you "
        "click. While AFTERLIFE holds a vigil for the widget, that click is a knock and brings it back.</p>"
        "<section class='partner'><h2>Acme Book Club</h2>"
        "<p class='tag'>What our members are reading this week, powered by Shelf.</p>"
        "<button id='load' type='button'>Load the Shelf widget</button>"
        "<div id='slot' class='slot empty'>The widget loads here.</div></section>"
        "<div id='log' class='log' aria-live='polite'></div>"
        "</main>" + SCRIPT + "</body></html>"
    )


@router.get("/partner", response_class=HTMLResponse)
def partner() -> str:
    return render()
