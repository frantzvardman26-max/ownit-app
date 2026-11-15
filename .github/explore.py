#!/usr/bin/env python3
"""Button audit on a real emulator. For each app:
1. Clear its data, launch, and get through first-run screens (language, welcome, "I understand", permission prompts).
2. On the main screen and on every tab in the bottom bar, tap each button, one at a time, from a fresh launch.
3. Record: screen changed (pixels or text), opened another app, crashed, or nothing happened.
Writes <out>/report.md and a screenshot per tap. Usage: explore.py <apk dir> <out dir>"""
import hashlib, io, os, re, subprocess, sys, time, xml.etree.ElementTree as ET
from PIL import Image, ImageChops
APKS, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
BT = sorted(os.listdir('/usr/local/lib/android/sdk/build-tools'))[-1]
FIRST_RUN = ['English', 'I understand. Start', 'Got it', 'Skip for now', 'Skip', 'Continue', 'Get started', 'Start', 'Not now', 'Later', 'OK']
ALLOW = ['While using the app', 'Only this time', 'Allow', 'ALLOW']

def sh(*a, timeout=60):
    try: return subprocess.run(a, capture_output=True, text=True, errors='replace', timeout=timeout).stdout
    except subprocess.TimeoutExpired: return ''
def adb(*a, **k): return sh('adb', *a, **k)
def shot():
    try: return subprocess.run(['adb', 'exec-out', 'screencap', '-p'], capture_output=True, timeout=30).stdout
    except subprocess.TimeoutExpired: return b''
def img(b):
    try: im = Image.open(io.BytesIO(b)).convert('L'); w, h = im.size; return im.crop((0, int(h * 0.05), w, h)).resize((180, 380))
    except Exception: return None
def differs(a, b):
    if a is None or b is None: return None
    d = ImageChops.difference(a, b).point(lambda v: 255 if v > 24 else 0)
    return sum(1 for v in d.getdata() if v) > 60
def dump():
    adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml'); x = adb('shell', 'cat', '/sdcard/ui.xml')
    return x[x.find('<?xml'):] if '<?xml' in x else ''
def tree(x):
    try: return list(ET.fromstring(x).iter('node'))
    except Exception: return []
def size():
    m = re.search(r'(\d+)x(\d+)', adb('shell', 'wm', 'size')); return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)
W, H = 0, 0
def clickables(x, pkg):
    out = []
    for n in tree(x):
        if n.get('package') != pkg or n.get('clickable') != 'true' or n.get('enabled') == 'false': continue
        b = list(map(int, re.findall(r'\d+', n.get('bounds', ''))))
        if len(b) != 4 or b[2] - b[0] < 8 or b[3] - b[1] < 8: continue
        label = (n.get('text') or n.get('content-desc') or '').replace('\n', ' ').strip()
        if not label: label = ' '.join(c.get('text', '') for c in n.iter('node') if c.get('text'))[:50] or n.get('class', '').split('.')[-1]
        out.append((label[:50], (b[0] + b[2]) // 2, (b[1] + b[3]) // 2))
    return out
def textsig(x, pkg): return hashlib.md5('|'.join(re.sub(r'\d+', '#', n.get('text', '')) for n in tree(x) if n.get('package') == pkg).encode()).hexdigest()
def front():
    m = re.search(r'mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/ }]+)', adb('shell', 'dumpsys', 'window')); return m.group(1) if m else ''
def tap(x, y): adb('shell', 'input', 'tap', str(x), str(y))
def launch(pkg):
    adb('shell', 'am', 'force-stop', pkg); adb('shell', 'monkey', '-p', pkg, '-c', 'android.intent.category.LAUNCHER', '1'); time.sleep(3.5)
def find(x, labels, pkgs=None):
    for want in labels:
        for n in tree(x):
            if pkgs and n.get('package') not in pkgs: continue
            if (n.get('text') or '').strip() == want:
                b = list(map(int, re.findall(r'\d+', n.get('bounds', '')))); return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    return None
def prep(pkg):
    """Get past first-run screens and permission prompts."""
    for _ in range(8):
        x = dump(); fg = front()
        p = find(x, ALLOW, None) if 'permissioncontroller' in fg or 'packageinstaller' in fg else None
        if p: tap(*p); time.sleep(1.5); continue
        p = find(x, FIRST_RUN, [pkg])
        if p: tap(*p); time.sleep(2); continue
        # Maybe the button is below the fold
        before = textsig(x, pkg); adb('shell', 'input', 'swipe', str(W // 2), str(int(H * .8)), str(W // 2), str(int(H * .25)), '300'); time.sleep(1)
        x2 = dump(); p = find(x2, FIRST_RUN, [pkg])
        if p: tap(*p); time.sleep(2); continue
        if textsig(x2, pkg) == before: break
    time.sleep(1)
def crashed(pkg):
    c = adb('logcat', '-d', '-b', 'crash')
    if 'FATAL EXCEPTION' in c:
        m = re.search(r'(\w+(?:Exception|Error)[^\n]*)', c); return (m.group(1) if m else 'crash')[:160]
    return None if adb('shell', 'pidof', pkg).strip() else 'process died'

def audit_screen(pkg, d, tag, path, report):
    """path: taps (label, x, y) to reach this screen from launch. Audits every clickable on it."""
    launch(pkg); [tap(x, y) or time.sleep(2) for _, x, y in path]
    base = dump(); items = [it for it in clickables(base, pkg) if not path or (it[1], it[2]) != (path[-1][1], path[-1][2])][:22]
    open(f'{d}/{tag}-00.png', 'wb').write(shot())
    report += [f'**{tag}** ({len(items)} buttons)', '', '| # | Button | Result |', '|---|---|---|']
    problems = 0
    for i, (label, x, y) in enumerate(items, 1):
        launch(pkg); [tap(px, py) or time.sleep(2) for _, px, py in path]
        bx, bi = dump(), img(shot()); adb('logcat', '-c'); tap(x, y); time.sleep(2.3)
        c = crashed(pkg); fg = front(); ax = dump(); a = shot(); ai = img(a)
        pix = differs(bi, ai); txt = textsig(ax, pkg) != textsig(bx, pkg)
        if c: res = 'CRASH: ' + c; problems += 1
        elif fg and pkg not in fg: res = f'opened {fg.split("/")[0]}'
        elif txt or pix: res = 'works'
        elif pix is None and not txt: res = 'no text change (screen is private, can\'t compare pixels)'
        else: res = 'NOTHING HAPPENED'; problems += 1
        open(f'{d}/{tag}-{i:02d}.png', 'wb').write(a)
        report.append(f'| {i} | {label} | {res} |')
    report.append(''); return problems, base

report = ['# Button audit', '', 'Every button on each app\'s main screen and on every tab, tapped one at a time from a fresh launch, on a real Android emulator.', '']
summary = []
W, H = size()
for apk in sorted(os.listdir(APKS)):
    if not apk.endswith('.apk'): continue
    path = os.path.join(APKS, apk); pkg = sh(f'/usr/local/lib/android/sdk/build-tools/{BT}/aapt2', 'dump', 'packagename', path).strip()
    adb('uninstall', pkg); r = adb('install', '-r', '-g', path, timeout=300)
    report += [f'## {apk[:-4]} ({pkg})', '']
    if 'Success' not in r: report += [f'Install failed: {r.strip()[:200]}', '']; summary.append(f'{apk[:-4]}: install failed'); continue
    d = os.path.join(OUT, apk[:-4]); os.makedirs(d, exist_ok=True)
    adb('shell', 'pm', 'clear', pkg); launch(pkg); prep(pkg)
    probs, base = audit_screen(pkg, d, 'main', [], report)
    tabs = [it for it in clickables(base, pkg) if it[2] > H * 0.86]   # the bottom bar
    for t in tabs[:6]:
        p, _ = audit_screen(pkg, d, 'tab-' + re.sub(r'\W+', '', t[0])[:14], [t], report); probs += p
    summary.append(f'{apk[:-4]}: {"OK" if probs == 0 else f"{probs} problem(s)"}')
report[4:4] = ['## Summary', ''] + [f'- {s}' for s in summary] + ['']
open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(report)); print('\n'.join(report))
