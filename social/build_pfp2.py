"""Profile pictures in the campaign's language: the rail seen through a letter,
misregistered blues, a dot screen. Sized for a 32px circle, not for a poster —
one letter, nothing else to read.
"""
import json, io, html

SP = r"C:\Users\eusta\AppData\Local\Temp\claude\C--Users-eusta-Desktop\9c8d616b-63d4-41c5-8dbb-f3ecc56925e9\scratchpad"
picks = json.load(open(SP + r"\picks.json", encoding="utf-8"))
frames = picks[3:4]        # a single frame keeps the letter readable when tiny

def sheet(cls):
    cells = "".join('<div class="cell"><img src="%s" alt=""></div>' % html.escape(p["photo"], quote=True)
                    for p in frames)
    return '<div class="sheet %s">%s</div>' % (cls, cells)

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:2160px;background:#050608;font-family:Epilogue,system-ui,sans-serif}
.tile{position:relative;width:1080px;height:1080px;overflow:hidden;background:#050608}

.sheet{position:absolute;inset:0;display:grid;grid-template-columns:1fr;grid-template-rows:1fr;gap:0}
.cell{position:relative;overflow:hidden;background:#0a0d12}
.cell img{width:100%;height:100%;object-fit:cover;object-position:50% 34%;
          filter:grayscale(1) contrast(1.05) brightness(1.12)}
.tone{position:absolute;inset:0;z-index:2;
      background:linear-gradient(120deg,#1b3ea8,#2f6bff 45%,#8fb4ff);
      mix-blend-mode:color;opacity:.6}
.dots{position:absolute;inset:0;z-index:3;opacity:.16;mix-blend-mode:multiply;
      background-image:radial-gradient(circle at center,#050608 1.3px,transparent 1.5px);
      background-size:7px 7px}
.cut{position:absolute;inset:0;z-index:4}
.cut svg{width:100%;height:100%;display:block}
.ring{position:absolute;inset:0;z-index:6;border-radius:50%;
      box-shadow:inset 0 0 0 3px rgba(47,107,255,.35)}
.scan{position:absolute;inset:0;z-index:6;opacity:.12;
  background:repeating-linear-gradient(180deg,rgba(255,255,255,.06) 0 1px,transparent 1px 5px)}
.grain{position:absolute;inset:0;z-index:6;opacity:.08;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E")}

/* B: the accent tile — the same letter, punched the other way round */
.solid{position:absolute;inset:0;background:#2f6bff}
.foot{position:absolute;left:0;right:0;bottom:96px;z-index:6;text-align:center;
      font-family:Anton,sans-serif;font-size:44px;letter-spacing:.36em;
      color:rgba(5,6,8,.75);padding-left:.36em}
"""

def letter_svg(plate, strokes):
    """One letter, cut out of `plate`, with the misregistered edges."""
    base = ('<text x="540" y="800" text-anchor="middle" font-family="Anton" '
            'font-size="900" %s>U</text>')
    out = ['<svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">',
           '<defs><mask id="m%s"><rect width="1080" height="1080" fill="#fff"/>' % plate[1:],
           base % 'fill="#000"',
           '</mask><filter id="s%s"><feGaussianBlur stdDeviation="14"/></filter></defs>' % plate[1:],
           '<rect width="1080" height="1080" fill="%s" fill-opacity="0.955" mask="url(#m%s)"/>'
           % (plate, plate[1:])]
    for dx, colour, width, extra in strokes:
        out.append(('<text x="%d" y="800" text-anchor="middle" font-family="Anton" '
                    'font-size="900" fill="none" stroke="%s" stroke-width="%d" %s>U</text>')
                   % (540 + dx, colour, width, extra))
    out.append('</svg>')
    return "".join(out)

A = letter_svg("#050608", [(-8, "#8fb4ff", 4, 'opacity=".55"'),
                           (8, "#1b3ea8", 4, 'opacity=".55"'),
                           (0, "#2f6bff", 6, ""),
                           (0, "#2f6bff", 14, 'opacity=".35" filter="url(#s050608)"')])

BODY = """
<div class="tile">
  {sheetA}
  <div class="tone"></div>
  <div class="dots"></div>
  <div class="cut">{svgA}</div>
  <div class="scan"></div><div class="grain"></div><div class="ring"></div>
</div>

<div class="tile">
  <div class="solid"></div>
  <div class="dots"></div>
  <div class="cut">{svgB}</div>
  <div class="foot">THE PLUG</div>
  <div class="scan"></div><div class="grain"></div>
</div>
"""

# B: the clothes sit inside the letter again, but the plate around it is the accent
B = ('<svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">'
     '<text x="532" y="800" text-anchor="middle" font-family="Anton" font-size="900"'
     ' fill="#8fb4ff" opacity=".55">U</text>'
     '<text x="548" y="800" text-anchor="middle" font-family="Anton" font-size="900"'
     ' fill="#1b3ea8" opacity=".55">U</text>'
     '<text x="540" y="800" text-anchor="middle" font-family="Anton" font-size="900"'
     ' fill="#050608">U</text></svg>')

doc = ('<!doctype html><html><head><meta charset="utf-8">\n'
       '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Epilogue:wght@400;600;800'
       '&display=swap" rel="stylesheet">\n<style>' + CSS + '</style></head><body>' +
       BODY.format(sheetA=sheet(""), svgA=A, svgB=B) +
       '</body></html>\n')

io.open(SP + r"\pfp2.html", "w", encoding="utf-8", newline="\n").write(doc)
print("profile marks built")
