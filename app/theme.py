"""Afterglass: the design system shared by Shelf's pages.

AFTERLIFE runs a forensic lab for dead code (a Coroner, a vigil, a Medium),
and the pages are that lab seen through frosted glass: translucent panels
floating over an obsidian field lit by slow spectral auras. Glass, because
an afterlife should feel weightless and quiet; a wide robotic display face
(Michroma) for anything ceremonial and a monospace for anything measured.

Colour is signal, never decoration:

    ice     pale blue    live, the vigil, data, links
    mint    green        measured savings, a feature in use
    aura    violet       resurrection, policy protection
    coral   red          failures and rollbacks

Plain CSS in the page, no build step. One small script reveals panels as
they scroll in and does nothing when the reader prefers reduced motion.
"""

FONTS = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Michroma&family=IBM+Plex+Mono:wght@400;500;600&display=swap'>"
)

# A toe tag with a hazard-yellow eyelet: the lab's mark in the browser tab.
FAVICON = (
    "<link rel='icon' href=\"data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%23050608'/%3E"
    "%3Cpath d='M10 6h14v20H8V8z' fill='%23d9dee6'/%3E"
    "%3Ccircle cx='12.5' cy='10.5' r='2' fill='%23a6dcff'/%3E"
    "%3Crect x='11' y='16' width='10' height='2' fill='%23050608'/%3E"
    "%3Crect x='11' y='20' width='7' height='2' fill='%23050608'/%3E%3C/svg%3E\">"
)

BASE = r"""
:root {
  color-scheme: dark;
  --bg: #050608; --glass: rgba(255, 255, 255, 0.035); --glass-hi: rgba(255, 255, 255, 0.06);
  --edge: rgba(255, 255, 255, 0.08); --edge-hi: rgba(255, 255, 255, 0.16); --sheen: rgba(255, 255, 255, 0.12);
  --ink: #eef2f7; --quiet: #9aa3b2; --faint: #5d6574;
  --ice: #a6dcff; --ice-soft: rgba(166, 220, 255, 0.12);
  --mint: #93f0c8; --mint-soft: rgba(147, 240, 200, 0.1);
  --aura: #c9a8ff; --aura-soft: rgba(201, 168, 255, 0.12);
  --coral: #ff8f86; --coral-soft: rgba(255, 143, 134, 0.12);
  /* semantic names the components use */
  --hazard: var(--ice); --hazard-soft: var(--ice-soft); --scan: var(--ice); --scan-soft: var(--ice-soft);
  --specimen: var(--mint); --specimen-soft: var(--mint-soft); --defib: var(--aura); --defib-soft: var(--aura-soft);
  --alarm: var(--coral); --alarm-soft: var(--coral-soft);
  --panel: var(--glass); --panel-hi: var(--glass-hi); --line: var(--edge); --line-hi: var(--edge-hi); --steel: var(--glass-hi);
  --accent: var(--ice); --good: var(--mint); --warn: var(--ice); --card: var(--glass); --stone: var(--glass-hi);
  --display: "Michroma", "Eurostile", "Bank Gothic", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Consolas, monospace;
  --radius: 20px; --blur: blur(22px) saturate(1.4);
  --ease: cubic-bezier(.2, .8, .1, 1);
}
* { box-sizing: border-box; }
html { background: var(--bg); scroll-behavior: smooth; overflow-x: clip; }
body { margin: 0; min-height: 100vh; overflow-x: clip; color: var(--ink); background: transparent;
  font: 400 14px/1.7 var(--mono); -webkit-font-smoothing: antialiased; }
/* the auras: slow spectral light behind the glass */
body::before, body::after { content: ""; position: fixed; z-index: -1; pointer-events: none; border-radius: 50%; filter: blur(90px); }
body::before { width: 820px; height: 820px; top: -300px; right: -180px; opacity: .9;
  background: radial-gradient(circle at 40% 40%, rgba(166, 220, 255, 0.45), rgba(120, 140, 255, 0.18) 45%, transparent 70%);
  animation: drift 26s ease-in-out infinite alternate; }
body::after { width: 760px; height: 760px; bottom: -300px; left: -220px; opacity: .75;
  background: radial-gradient(circle at 60% 50%, rgba(201, 168, 255, 0.4), rgba(147, 240, 200, 0.12) 50%, transparent 70%);
  animation: drift 32s ease-in-out infinite alternate-reverse; }
::selection { background: var(--ice); color: var(--bg); }
main { max-width: 1120px; margin: 0 auto; padding: 0 28px 110px; }
a { color: var(--ice); text-decoration: none; transition: color .2s, opacity .2s; }
a:hover { color: var(--ink); }
code, .mono { font-family: var(--mono); font-size: 0.92em; }
code { color: var(--ice); background: var(--ice-soft); padding: 1px 7px; border-radius: 6px; }
b, strong { font-weight: 600; }

/* --- glass ---------------------------------------------------------------- */
.glass { background: linear-gradient(180deg, var(--glass-hi), var(--glass)); border: 1px solid var(--edge);
  border-radius: var(--radius); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  box-shadow: inset 0 1px 0 var(--sheen), 0 30px 60px -40px rgba(0, 0, 0, 0.8); }

/* --- navigation ------------------------------------------------------------ */
nav { position: sticky; top: 14px; z-index: 50; display: flex; align-items: center; gap: 6px; margin: 14px 0 0; padding: 8px 8px 8px 20px;
  background: rgba(14, 16, 22, 0.55); border: 1px solid var(--edge); border-radius: 999px;
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); box-shadow: inset 0 1px 0 var(--sheen);
  font: 400 10.5px/1 var(--display); letter-spacing: 0.14em; text-transform: uppercase; }
nav .brand { display: inline-flex; align-items: center; gap: 12px; margin-right: auto; color: var(--ink); font: 400 13px/1 var(--display); letter-spacing: 0.3em; }
nav .brand i { width: 8px; height: 8px; border-radius: 50%; background: var(--ice); box-shadow: 0 0 14px var(--ice); }
nav .brand small { font: 400 10.5px/1 var(--mono); letter-spacing: 0.06em; color: var(--faint); text-transform: none; }
nav a:not(.brand) { color: var(--quiet); padding: 11px 16px; border-radius: 999px; transition: background .2s, color .2s; }
nav a:not(.brand):hover { color: var(--ink); background: var(--glass-hi); }
nav a[aria-current] { color: var(--ink); background: rgba(255, 255, 255, 0.09); box-shadow: inset 0 1px 0 var(--sheen); }
nav .watch { display: inline-flex; align-items: center; gap: 8px; margin-left: 6px; padding: 10px 14px; border-radius: 999px;
  color: var(--mint); background: var(--mint-soft); font: 500 10.5px/1 var(--mono); letter-spacing: 0.1em; }
nav .watch b { width: 6px; height: 6px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 10px var(--mint); font-size: 0;
  animation: breathe 2.4s ease-in-out infinite; }
@media (max-width: 720px) { nav .brand small, nav .watch { display: none; } }

/* --- hero ------------------------------------------------------------------ */
.hero { padding: 96px 0 56px; }
.case { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; margin-bottom: 34px;
  font: 400 11px/1 var(--mono); letter-spacing: 0.14em; text-transform: uppercase; color: var(--faint); }
.case .id { color: var(--ice); }
.case .sep { flex: 0 0 40px; height: 1px; background: var(--edge-hi); }
.case .barcode { display: none; }
.eyebrow { font: 400 11px/1 var(--display); letter-spacing: 0.32em; text-transform: uppercase; color: var(--quiet); margin-bottom: 22px; }
h1 { margin: 0; max-width: 16ch; font: 400 clamp(36px, 6.2vw, 78px)/1.08 var(--display); letter-spacing: -0.01em; text-transform: uppercase; }
h1 em { font-style: normal; background: linear-gradient(100deg, var(--ice) 10%, var(--aura) 70%, var(--mint));
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.lead { max-width: 600px; margin: 30px 0 0; color: var(--quiet); font-size: 14.5px; line-height: 1.8; }
.lead em { font-style: normal; color: var(--ink); }

/* --- section headings ------------------------------------------------------ */
h2 { display: flex; align-items: baseline; gap: 16px; margin: 120px 0 10px; scroll-margin-top: 100px;
  font: 400 clamp(20px, 2.4vw, 28px)/1.2 var(--display); letter-spacing: 0.04em; text-transform: uppercase; }
h2::before { content: attr(data-index); font: 400 11px/1 var(--mono); letter-spacing: 0.1em; color: var(--faint); }
h2:not([data-index])::before { display: none; }
h2 .count { font: 400 12px/1 var(--mono); color: var(--ice); }
h2 + .lead { margin: 0 0 28px; font-size: 13.5px; }

/* --- glass tables ---------------------------------------------------------- */
.scroll { overflow-x: auto; background: linear-gradient(180deg, var(--glass-hi), var(--glass)); border: 1px solid var(--edge);
  border-radius: var(--radius); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); box-shadow: inset 0 1px 0 var(--sheen); }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th { padding: 16px 20px 12px; text-align: left; white-space: nowrap; font: 400 9.5px/1 var(--display); letter-spacing: 0.2em;
  text-transform: uppercase; color: var(--faint); }
td { padding: 16px 20px; border-top: 1px solid var(--edge); vertical-align: top; color: var(--quiet); }
td b { color: var(--ink); font: 400 12px/1.4 var(--display); letter-spacing: 0.08em; text-transform: uppercase; }
td .mono { color: var(--ice); }
tr { transition: background .2s; }
tr:hover td { background: rgba(255, 255, 255, 0.025); }
th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); }
th.num { color: var(--faint); }
.pill { display: inline-flex; align-items: center; gap: 7px; padding: 5px 11px; border-radius: 999px; white-space: nowrap;
  font: 500 11px/1 var(--mono); letter-spacing: 0.04em; color: var(--quiet); background: var(--glass-hi); }
.pill::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
.pill.alive, .pill.read { color: var(--mint); background: var(--mint-soft); }
.pill.candidate, .pill.reading { color: var(--ice); background: var(--ice-soft); }
.pill.protected { color: var(--aura); background: var(--aura-soft); }
.pill.quiet, .pill.to-read { color: var(--faint); }
.empty { color: var(--faint); font-size: 13px; margin: 14px 0; padding: 22px; border-radius: var(--radius); border: 1px dashed var(--edge); }

footer { margin-top: 130px; padding-top: 24px; border-top: 1px solid var(--edge); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 18px; color: var(--faint); font-size: 12px; }
footer .epitaph { font: 400 10.5px/1 var(--display); letter-spacing: 0.3em; text-transform: uppercase; color: var(--quiet); }

/* --- motion ---------------------------------------------------------------- */
@keyframes drift { from { transform: translate(0, 0) scale(1); } to { transform: translate(-60px, 40px) scale(1.12); } }
@keyframes breathe { 50% { opacity: .35; } }
@keyframes rise { from { opacity: 0; transform: translateY(14px); filter: blur(6px); } to { opacity: 1; transform: none; filter: none; } }
@keyframes scanline { from { transform: translateX(-100%); } to { transform: translateX(400%); } }
@keyframes blink { to { visibility: hidden; } }
.hero > * { animation: rise 1.1s var(--ease) both; }
.hero > *:nth-child(2) { animation-delay: .1s; } .hero > *:nth-child(3) { animation-delay: .2s; }
.hero > *:nth-child(4) { animation-delay: .32s; }
.reveal { opacity: 0; transform: translateY(16px); transition: opacity .9s var(--ease), transform .9s var(--ease); }
.reveal.seen { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .reveal { opacity: 1; transform: none; }
}
"""

# Reveals panels as they scroll into view; content stays visible without JS.
REVEAL_SCRIPT = """<script>
(function () {
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('seen'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('[data-reveal]').forEach(function (el) { el.classList.add('reveal'); io.observe(el); });
})();
</script>"""


def head(title: str, style: str) -> str:
    """Everything up to and including <body>, the same on every page."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<meta name='theme-color' content='#050608'>"
        f"<title>{title}</title>{FAVICON}{FONTS}<style>{BASE}{style}</style></head><body>"
    )


def case_header(case_id: str, label: str) -> str:
    """The strip above a hero: case number, label, a rule and a barcode."""
    return (f"<div class='case'><span class='id'>{case_id}</span><span>{label}</span>"
            "<span class='sep'></span><span class='barcode' aria-hidden='true'></span></div>")
