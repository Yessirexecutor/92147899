# fix_devpng_views.py — real dev.png badge + 1 view per account. Run: python fix_devpng_views.py
import os, struct, zlib

# ---------- 1. generate public/dev.png (pure python, no Pillow) ----------
def make_dev_png(path):
    W, H = 34, 20
    top, bot = (254, 44, 85), (122, 60, 255)          # red->purple gradient
    font = {'D': ["110","101","101","101","110"],
            'E': ["111","100","110","100","111"],
            'V': ["101","101","101","101","010"]}
    px = [[(0,0,0,0)]*W for _ in range(H)]
    r = 6
    def inside(x, y):
        for cx, cy in ((r,r),(W-1-r,r),(r,H-1-r),(W-1-r,H-1-r)):
            if (x< r or x> W-1-r) and (y< r or y> H-1-r):
                if (x-cx)**2 + (y-cy)**2 > r*r: return False
        return True
    for y in range(H):
        t = y/(H-1)
        col = tuple(int(a+(b-a)*t) for a,b in zip(top,bot)) + (255,)
        for x in range(W):
            if inside(x, y): px[y][x] = col
    sx, sy, sc = 6, 5, 2
    for ch in "DEV":
        for gy, row in enumerate(font[ch]):
            for gx, c in enumerate(row):
                if c == '1':
                    for dy in range(sc):
                        for dx in range(sc):
                            px[sy+gy*sc+dy][sx+gx*sc+dx] = (255,255,255,255)
        sx += 3*sc + 2
    raw = b''.join(b'\x00' + b''.join(struct.pack('4B', *p) for p in row) for row in px)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t+d) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    open(path, 'wb').write(png)

os.makedirs("public", exist_ok=True)
make_dev_png(os.path.join("public", "dev.png"))
print("[ok]   generated public/dev.png (34x20 red->purple DEV badge)")

# ---------- 2. use the PNG in index.html ----------
p = os.path.join("public", "index.html")
src = open(p, encoding="utf-8").read()

def patch(s, old, new, label, count_all=True):
    if old in s:
        s = s.replace(old, new) if count_all else s.replace(old, new, 1)
        print("[ok]  ", label); return s
    if new in s:
        print("[skip]", label, "(already)"); return s
    print("[!!]  NOT FOUND:", label); return s

# swap the CSS-drawn badge for the real PNG (appears in card template + comments template)
src = patch(src, '<span class="devtag">DEV</span>',
            '<img class="devpng" src="/dev.png" alt="DEV">',
            "PNG badge on feed + comments")

# badge on the profile page header too
src = patch(src, "@${esc(u.username)}</h2>",
            "@${esc(u.username)}${u.username==='vybe'?' <img class=\"devpng\" src=\"/dev.png\" alt=\"DEV\">':''}</h2>",
            "PNG badge on profile header", count_all=False)

if 'id="devpngcss"' not in src:
    css = ('<style id="devpngcss">.devpng{display:inline-block;height:15px;vertical-align:-3px;'
           'margin-left:6px;border-radius:4px;box-shadow:0 0 10px rgba(254,44,85,.7)}</style></head>')
    src = src.replace("</head>", css, 1)
    print("[ok]   badge styles")
open(p, "w", encoding="utf-8", newline="\n").write(src)

# ---------- 3. server.js: unique views + auto-create table at boot ----------
q = "server.js"
s = open(q, encoding="utf-8").read()

s = patch(s, "const TOKEN_DAYS = 30",
"""await sql`CREATE TABLE IF NOT EXISTS video_views (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, video_id))`
await sql`CREATE INDEX IF NOT EXISTS idx_video_views_video ON video_views (video_id)`

const TOKEN_DAYS = 30""", "auto-create video_views table at startup", count_all=False)

old_view = ("app.post('/api/videos/:id/view', async req => {\n"
"  await sql`UPDATE videos SET views = views + 1 WHERE id = ${Number(req.params.id)}`\n"
"  return {}\n})")
new_view = ("app.post('/api/videos/:id/view', async req => {\n"
"  const id = Number(req.params.id)\n"
"  if (!req.user) return {}\n"
"  const ins = await sql`INSERT INTO video_views (user_id, video_id) VALUES (${req.user.id}, ${id}) "
"ON CONFLICT DO NOTHING RETURNING video_id`\n"
"  if (ins.length) await sql`UPDATE videos SET views = views + 1 WHERE id = ${id}`\n"
"  return {}\n})")
s = patch(s, old_view, new_view, "views = 1 per account (dedup table)")

open(q, "w", encoding="utf-8", newline="\n").write(s)
print("\nDone. RESTART the server (Ctrl+C -> node --env-file=.env server.js), then Ctrl+F5.")
