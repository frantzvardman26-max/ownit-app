#!/usr/bin/env python3
"""SQL for a free Vindie ad started by Frantz (friends, house ads). Picture is fetched, cropped to 1200x628 and embedded."""
import base64, io, os, re, secrets, urllib.request, datetime
from PIL import Image
def q(s): return "'" + str(s).replace("'", "''") + "'"
biz, head, body, url = os.environ['BIZ'][:60], os.environ['HEADLINE'][:40], os.environ.get('BODY', '')[:90], os.environ['URL'][:400]
tier = os.environ.get('TIER', 'featured'); weeks = max(1, min(52, int(os.environ.get('WEEKS', '1'))))
assert re.match(r'^https://\S+\.\S+$', url) and tier in ('starter', 'boost', 'featured')
img = ''
if os.environ.get('IMG_URL'):
    raw = urllib.request.urlopen(urllib.request.Request(os.environ['IMG_URL'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert('RGB'); W, H = 1200, 628; k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k))); l, t = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((l, t, l + W, t + H))
    # one SQL statement must stay under ~100 KB, so keep the picture under 85 KB
    for w, qual in ((1200, 72), (1200, 60), (1000, 60), (900, 55), (800, 50)):
        b = io.BytesIO(); im.resize((w, round(w * 628 / 1200))).save(b, 'JPEG', quality=qual, optimize=True); img = 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
        if len(img) < 85000: break
now = datetime.datetime.now(datetime.timezone.utc); end = now + datetime.timedelta(weeks=weeks); iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
code = 'VA-' + ''.join(secrets.choice('ABCDEFGHJKMNPQRSTUVWXYZ23456789') for _ in range(6))
open('comp.sql', 'w').write("INSERT INTO vindie_ads (code, key, biz, email, headline, body, url, img, tier, weeks, status, created, starts, ends, note) SELECT "
    f"{q(code)}, {q(secrets.token_hex(10))}, {q(biz)}, '', {q(head)}, {q(body)}, {q(url)}, {q(img)}, {q(tier)}, {weeks}, 'running', {q(iso(now))}, {q(iso(now))}, {q(iso(end))}, 'free' "
    f"WHERE NOT EXISTS (SELECT 1 FROM vindie_ads WHERE biz = {q(biz)} AND note = 'free' AND ends > {q(iso(now))});\n")
print('ad', code, tier, weeks, 'weeks, picture bytes', len(img))
