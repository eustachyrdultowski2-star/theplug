"""Four profile marks, none of them a letter in a circle.

The idea the name was asking for: a wall plug is a U with two prongs, so the
accent letter of the wordmark and the object it is named after are the same
shape. Everything below is that observation, argued four ways.
"""
import io

SP = r"C:\Users\eusta\AppData\Local\Temp\claude\C--Users-eusta-Desktop\9c8d616b-63d4-41c5-8dbb-f3ecc56925e9\scratchpad"

# --- geometry, shared by every mark -----------------------------------------
# a U drawn as one thick stroke, with two prongs standing on its arms
ARM_L, ARM_R = 390, 690
TOP, BEND = 430, 620
W = 132                     # stroke weight of the body
PRONG_W, PRONG_H = 86, 150

def plug(colour, prong_colour=None, sw=W):
    prong_colour = prong_colour or colour
    return f"""
    <path d="M {ARM_L} {TOP} L {ARM_L} {BEND} A {(ARM_R-ARM_L)/2} {(ARM_R-ARM_L)/2} 0 0 0 {ARM_R} {BEND} L {ARM_R} {TOP}"
          fill="none" stroke="{colour}" stroke-width="{sw}" stroke-linecap="butt"/>
    <rect x="{ARM_L-PRONG_W/2}" y="{TOP-PRONG_H-46}" width="{PRONG_W}" height="{PRONG_H}" rx="18" fill="{prong_colour}"/>
    <rect x="{ARM_R-PRONG_W/2}" y="{TOP-PRONG_H-46}" width="{PRONG_W}" height="{PRONG_H}" rx="18" fill="{prong_colour}"/>
    """

def socket(colour):
    """The other half of the joke: the wall, with two slots waiting."""
    return f"""
    <rect x="474" y="360" width="60" height="190" rx="26" fill="{colour}"/>
    <rect x="546" y="360" width="60" height="190" rx="26" fill="{colour}"/>
    <rect x="470" y="640" width="140" height="52" rx="26" fill="{colour}" opacity=".55"/>
    """

HEAD = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:4320px;background:#050608}
.tile{position:relative;width:1080px;height:1080px;overflow:hidden}
.tile svg{position:absolute;inset:0;width:100%;height:100%}
.dots{position:absolute;inset:0;z-index:3;opacity:.14;mix-blend-mode:multiply;
      background-image:radial-gradient(circle at center,#050608 1.3px,transparent 1.5px);
      background-size:7px 7px}
.grain{position:absolute;inset:0;z-index:4;opacity:.07;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E")}
.cap{position:absolute;left:0;right:0;bottom:104px;z-index:5;text-align:center;
     font-family:'JetBrains Mono',monospace;font-size:30px;letter-spacing:.34em;
     text-transform:uppercase}
</style></head><body>
"""

# 1 — the accent field, the plug punched out of it
one = f"""<div class="tile" style="background:#2f6bff">
  <svg viewBox="0 0 1080 1080">{plug("#050608")}</svg>
  <div class="dots"></div><div class="grain"></div>
</div>"""

# 2 — dark field, the plug live in blue with a filament glow
two = f"""<div class="tile" style="background:#07080a">
  <svg viewBox="0 0 1080 1080">
    <defs><filter id="glow"><feGaussianBlur stdDeviation="26"/></filter></defs>
    <g filter="url(#glow)" opacity=".85">{plug("#2f6bff", sw=W)}</g>
    {plug("#8fb4ff", "#eaf1ff", sw=W-44)}
  </svg>
  <div class="grain"></div>
</div>"""

# 3 — the socket, plate and all: the wall the plug goes into
three = f"""<div class="tile" style="background:#e9ecf2">
  <svg viewBox="0 0 1080 1080">
    <circle cx="540" cy="520" r="300" fill="#0a0d12"/>
    {socket("#e9ecf2")}
  </svg>
  <div class="dots"></div>
  <div class="cap" style="color:#0a0d12">THE PLUG</div>
</div>"""

# 4 — the mark as a stamp: heavy ring, off-register, blue on black
four = f"""<div class="tile" style="background:#050608">
  <svg viewBox="0 0 1080 1080">
    <circle cx="540" cy="540" r="392" fill="none" stroke="#1b3ea8" stroke-width="26" opacity=".7"
            transform="translate(10,0)"/>
    <circle cx="540" cy="540" r="392" fill="none" stroke="#2f6bff" stroke-width="26"/>
    <g transform="translate(-9,0)" opacity=".6">{plug("#8fb4ff")}</g>
    {plug("#2f6bff")}
  </svg>
  <div class="dots"></div><div class="grain"></div>
</div>"""

io.open(SP + r"\marks.html", "w", encoding="utf-8", newline="\n").write(
    HEAD + one + two + three + four + "</body></html>\n")
print("four marks built")
