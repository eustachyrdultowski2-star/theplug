"""Build the Instagram triptych: one contact sheet of real catalogue pieces,
the wordmark cut out of the dark so the rail shows through it."""
import json, io, html

SP = r"C:\Users\eusta\AppData\Local\Temp\claude\C--Users-eusta-Desktop\9c8d616b-63d4-41c5-8dbb-f3ecc56925e9\scratchpad"
picks = json.load(open(SP + r"\picks.json", encoding="utf-8"))
cells = "".join('<div class="cell"><img src="%s" alt=""></div>' % html.escape(p["photo"], quote=True)
                for p in picks)
caps = picks[:2]

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:3240px;height:1350px;background:#07080a;overflow:hidden;position:relative;
     font-family:Epilogue,system-ui,sans-serif;color:#f4f5f7}
.sheet{position:absolute;inset:0;display:grid;grid-template-columns:repeat(7,1fr);
       grid-template-rows:repeat(3,1fr);gap:0;background:#111318}
.cell{position:relative;overflow:hidden;background:#0d0f13}
.cell img{width:100%;height:100%;object-fit:cover;filter:grayscale(1) contrast(1.18) brightness(.82)}
.sheet::after{content:"";position:absolute;inset:0;background:#2f6bff;mix-blend-mode:color;opacity:.55}
.sheet::before{content:"";position:absolute;inset:0;z-index:2;
              background:linear-gradient(180deg,rgba(7,8,10,.55),rgba(7,8,10,.15) 40%,rgba(7,8,10,.85))}
.cut{position:absolute;inset:0;z-index:3}
.cut svg{width:100%;height:100%;display:block}
.rule{position:absolute;left:0;right:0;height:1px;background:rgba(244,245,247,.16);z-index:5}
.vrule{position:absolute;top:0;bottom:0;width:1px;background:rgba(244,245,247,.10);z-index:5}
.idx{position:absolute;z-index:6;font-family:'JetBrains Mono',monospace;font-size:26px;
     letter-spacing:.18em;color:#8f939c}
.cap{position:absolute;z-index:6;font-family:'JetBrains Mono',monospace;font-size:22px;
     line-height:1.5;color:#c8ccd4;letter-spacing:.02em}
.cap b{color:#f4f5f7;font-weight:500}
.cap i{font-style:normal;color:#2f6bff}
.bar{position:absolute;z-index:6;background:#2f6bff;color:#07080a;font-family:Anton,sans-serif;
     font-size:40px;letter-spacing:.22em;padding:16px 34px 12px;white-space:nowrap}
.foot{position:absolute;bottom:64px;z-index:6;font-family:'JetBrains Mono',monospace;font-size:24px;
      letter-spacing:.2em;text-transform:uppercase;color:#a1a4ad;white-space:nowrap}
.mark{position:absolute;z-index:6;font-family:Anton,sans-serif;font-size:34px;
      letter-spacing:.52em;color:#f4f5f7}
.reg{position:absolute;z-index:6;width:26px;height:26px}
.reg::before,.reg::after{content:"";position:absolute;background:rgba(244,245,247,.5)}
.reg::before{left:0;right:0;top:12px;height:1px}
.reg::after{top:0;bottom:0;left:12px;width:1px}
.scan{position:absolute;inset:0;z-index:7;opacity:.16;
  background:repeating-linear-gradient(180deg,rgba(255,255,255,.05) 0 1px,transparent 1px 4px)}
.grain{position:absolute;inset:0;z-index:7;opacity:.07;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E")}
.seam{position:absolute;top:0;bottom:0;width:2px;background:rgba(7,8,10,.65);z-index:8}
"""

BODY = """
<div class="sheet">{cells}</div>

<div class="cut">
  <svg viewBox="0 0 3240 1350" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <mask id="hole">
        <rect width="3240" height="1350" fill="#fff"/>
        <text x="1620" y="950" text-anchor="middle" font-family="Anton" font-size="1040" fill="#000">PLUG</text>
      </mask>
    </defs>
    <rect width="3240" height="1350" fill="#07080a" fill-opacity="0.94" mask="url(#hole)"/>
    <text x="1620" y="950" text-anchor="middle" font-family="Anton" font-size="1040"
          fill="none" stroke="#2f6bff" stroke-width="5" opacity=".9">PLUG</text>
  </svg>
</div>

<div class="rule" style="top:150px"></div>
<div class="rule" style="bottom:150px"></div>
<div class="vrule" style="left:1080px"></div>
<div class="vrule" style="left:2160px"></div>

<div class="mark" style="left:88px;top:82px">THE PLUG</div>
<div class="idx" style="right:96px;top:88px">EST. 2026 \u2014 548 BRANDS</div>

<div class="idx" style="left:88px;top:1216px">01</div>
<div class="idx" style="left:1168px;top:1216px;color:#5c616b">02</div>
<div class="idx" style="left:2248px;top:1216px">03</div>

<div class="cap" style="left:88px;top:210px">
  <b>{b1}</b><br>{n1}<br><i>{p1}</i>
</div>
<div class="cap" style="right:96px;top:210px;text-align:right">
  <b>{b2}</b><br>{n2}<br><i>{p2}</i>
</div>

<div class="bar" style="left:1620px;top:1176px;transform:translateX(-50%)">COMING SOON</div>

<div class="foot" style="left:88px">Paste a TikTok</div>
<div class="foot" style="right:96px">theplug.co</div>

<div class="reg" style="left:60px;top:54px"></div>
<div class="reg" style="right:60px;bottom:54px"></div>

<div class="seam" style="left:1079px"></div>
<div class="seam" style="left:2159px"></div>
<div class="scan"></div>
<div class="grain"></div>
"""

doc = ('<!doctype html><html><head><meta charset="utf-8">\n'
       '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Epilogue:wght@400;500;600;700;800'
       '&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">\n'
       '<style>' + CSS + '</style></head><body>' +
       BODY.format(cells=cells,
                   b1=html.escape(caps[0]["brand"]), n1=html.escape(caps[0]["name"][:30]),
                   p1=html.escape(caps[0]["price"]),
                   b2=html.escape(caps[1]["brand"]), n2=html.escape(caps[1]["name"][:30]),
                   p2=html.escape(caps[1]["price"])) +
       '</body></html>\n')

io.open(SP + r"\ig_advanced.html", "w", encoding="utf-8", newline="\n").write(doc)
print("rebuilt with", len(picks), "pieces;", caps[0]["price"], caps[1]["price"])
