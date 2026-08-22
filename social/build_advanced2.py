"""Campaign, second pass: bigger crops, halftone, a chromatic split on the
wordmark, and no names or prices anywhere — the clothes carry it."""
import json, io, html

SP = r"C:\Users\eusta\AppData\Local\Temp\claude\C--Users-eusta-Desktop\9c8d616b-63d4-41c5-8dbb-f3ecc56925e9\scratchpad"
picks = json.load(open(SP + r"\picks.json", encoding="utf-8"))

# eight big frames read as photography; twenty-one small ones read as a mosaic
frames = picks[:8]
cells = "".join('<div class="cell"><img src="%s" alt=""></div>' % html.escape(p["photo"], quote=True)
                for p in frames)

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:3240px;height:1350px;background:#050608;overflow:hidden;position:relative;
     font-family:Epilogue,system-ui,sans-serif;color:#f4f5f7}

/* the rail, in four wide frames per row */
.sheet{position:absolute;inset:0;display:grid;grid-template-columns:repeat(4,1fr);
       grid-template-rows:repeat(2,1fr);gap:0}
.cell{position:relative;overflow:hidden;background:#0a0d12}
.cell img{width:100%;height:100%;object-fit:cover;object-position:50% 38%;
          filter:grayscale(1) contrast(1.14) brightness(1.16)}
.tone{position:absolute;inset:0;z-index:2;background:
      linear-gradient(115deg,#1b3ea8 0%,#2f6bff 42%,#8fb4ff 100%);
      mix-blend-mode:color;opacity:.58}
.dark{position:absolute;inset:0;z-index:3;
      background:radial-gradient(ellipse 70% 80% at 50% 46%,rgba(5,6,8,.02),rgba(5,6,8,.66) 82%)}
/* print, not screen: a dot screen over the photography */
.dots{position:absolute;inset:0;z-index:4;opacity:.14;mix-blend-mode:multiply;
      background-image:radial-gradient(circle at center,#050608 1.4px,transparent 1.6px);
      background-size:7px 7px}

/* the wordmark is the window; two offset strokes give it a printing-press edge */
.cut{position:absolute;inset:0;z-index:5}
.cut svg{width:100%;height:100%;display:block}

.hair{position:absolute;left:0;right:0;height:1px;background:rgba(47,107,255,.55);z-index:6}
.vrule{position:absolute;top:0;bottom:0;width:1px;background:rgba(244,245,247,.08);z-index:6}
.mark{position:absolute;z-index:7;font-family:Anton,sans-serif;font-size:34px;
      letter-spacing:.52em;color:#f4f5f7}
.meta{position:absolute;z-index:7;font-family:'JetBrains Mono',monospace;font-size:24px;
      letter-spacing:.2em;color:#7d818b;text-transform:uppercase;white-space:nowrap}
.hint{position:absolute;top:1012px;z-index:7;font-family:'JetBrains Mono',monospace;
      font-size:26px;letter-spacing:.24em;text-transform:uppercase;color:#9aa0ab;white-space:nowrap}
.hint b{color:#2f6bff;font-weight:500}
.stat{position:absolute;bottom:74px;z-index:7;font-family:Anton,sans-serif;font-size:44px;
      letter-spacing:.14em;color:#f4f5f7;white-space:nowrap}
.stat small{display:block;font-family:'JetBrains Mono',monospace;font-size:19px;
      letter-spacing:.26em;color:#7d818b;margin-top:8px;font-weight:400}
.bar{position:absolute;z-index:7;background:#2f6bff;color:#050608;font-family:Anton,sans-serif;
     font-size:42px;letter-spacing:.24em;padding:18px 40px 14px;white-space:nowrap;
     box-shadow:0 0 0 1px rgba(143,180,255,.5), 0 24px 60px rgba(47,107,255,.35)}
.reg{position:absolute;z-index:7;width:30px;height:30px;opacity:.55}
.reg::before,.reg::after{content:"";position:absolute;background:#f4f5f7}
.reg::before{left:0;right:0;top:14px;height:1px}
.reg::after{top:0;bottom:0;left:14px;width:1px}
.scan{position:absolute;inset:0;z-index:8;opacity:.14;
  background:repeating-linear-gradient(180deg,rgba(255,255,255,.06) 0 1px,transparent 1px 5px)}
.grain{position:absolute;inset:0;z-index:8;opacity:.08;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E")}
.vig{position:absolute;inset:0;z-index:8;
     background:radial-gradient(ellipse 78% 86% at 50% 50%,transparent 55%,rgba(5,6,8,.72))}
.seam{position:absolute;top:0;bottom:0;width:2px;background:rgba(5,6,8,.7);z-index:9}
"""

BODY = """
<div class="sheet">{cells}</div>
<div class="tone"></div>
<div class="dark"></div>
<div class="dots"></div>

<div class="cut">
  <svg viewBox="0 0 3240 1350" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <mask id="hole">
        <rect width="3240" height="1350" fill="#fff"/>
        <text x="1620" y="960" text-anchor="middle" font-family="Anton" font-size="1120" fill="#000">PLUG</text>
      </mask>
      <filter id="soft"><feGaussianBlur stdDeviation="18"/></filter>
    </defs>

    <!-- the plate, with the word punched out of it -->
    <rect width="3240" height="1350" fill="#050608" fill-opacity="0.955" mask="url(#hole)"/>

    <!-- misregistration, the way a two-colour print never lines up -->
    <text x="1611" y="960" text-anchor="middle" font-family="Anton" font-size="1120"
          fill="none" stroke="#8fb4ff" stroke-width="4" opacity=".55">PLUG</text>
    <text x="1629" y="960" text-anchor="middle" font-family="Anton" font-size="1120"
          fill="none" stroke="#1b3ea8" stroke-width="4" opacity=".55">PLUG</text>
    <text x="1620" y="960" text-anchor="middle" font-family="Anton" font-size="1120"
          fill="none" stroke="#2f6bff" stroke-width="6">PLUG</text>
    <text x="1620" y="960" text-anchor="middle" font-family="Anton" font-size="1120"
          fill="none" stroke="#2f6bff" stroke-width="16" opacity=".35" filter="url(#soft)">PLUG</text>
  </svg>
</div>

<div class="hair" style="top:963px"></div>
<div class="vrule" style="left:1080px"></div>
<div class="vrule" style="left:2160px"></div>

<div class="mark" style="left:92px;top:86px">THE PLUG</div>
<div class="meta" style="right:100px;top:92px">NO. 001 / EST. 2026</div>

<div class="hint" style="left:92px">Paste a TikTok</div>
<div class="hint" style="left:1620px;transform:translateX(-50%)">Get <b>every brand</b> in the fit</div>
<div class="hint" style="right:100px">theplug.co</div>

<div class="stat" style="left:92px">548<small>BRANDS</small></div>
<div class="stat" style="right:100px;text-align:right">2,350<small>PIECES</small></div>
<div class="bar" style="left:1620px;top:1132px;transform:translateX(-50%)">COMING SOON</div>

<div class="reg" style="left:56px;top:52px"></div>
<div class="reg" style="right:56px;bottom:52px"></div>

<div class="seam" style="left:1079px"></div>
<div class="seam" style="left:2159px"></div>
<div class="scan"></div>
<div class="grain"></div>
<div class="vig"></div>
"""

doc = ('<!doctype html><html><head><meta charset="utf-8">\n'
       '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Epilogue:wght@400;500;600;700;800'
       '&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">\n'
       '<style>' + CSS + '</style></head><body>' + BODY.format(cells=cells) + '</body></html>\n')

io.open(SP + r"\ig_advanced2.html", "w", encoding="utf-8", newline="\n").write(doc)
print("built with", len(frames), "frames, no names, no prices")
