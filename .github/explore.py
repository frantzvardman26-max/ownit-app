#!/usr/bin/env python3
"""Taps every clickable thing on each app's first screen, one at a time from a fresh launch, on a real emulator.
For each tap: did the screen change, did nothing visible happen, did the app crash, or did it open another app?
Writes explore/report.md and a screenshot per tap. Usage: explore.py <apk dir> <out dir>"""
import hashlib, os, re, subprocess, sys, time, xml.etree.ElementTree as ET
APKS, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
BT = sorted(os.listdir('/usr/local/lib/android/sdk/build-tools'))[-1]
def sh(*a, timeout=60):
    try: return subprocess.run(a, capture_output=True, text=True, errors='replace', timeout=timeout).stdout
    except subprocess.TimeoutExpired: return ''
def adb(*a, **k): return sh('adb', *a, **k)
def dump():
    adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml'); x = adb('shell', 'cat', '/sdcard/ui.xml')
    return x[x.find('<?xml'):] if '<?xml' in x else ''
def nodes(x, pkg):
    out = []
    try: root = ET.fromstring(x)
    except Exception: return out
    for n in root.iter('node'):
        if n.get('package') != pkg or n.get('clickable') != 'true' or n.get('enabled') == 'false': continue
        b = list(map(int, re.findall(r'\d+', n.get('bounds', '')))); 
        if len(b) != 4 or b[2] - b[0] < 8 or b[3] - b[1] < 8: continue
        label = (n.get('text') or n.get('content-desc') or '').replace('\n', ' ').strip() or n.get('class', '').split('.')[-1]
        out.append((label[:50], (b[0] + b[2]) // 2, (b[1] + b[3]) // 2))
    return out
def sig(x, pkg):  # what's on screen, ignoring things that tick (times)
    texts = [n.get('text', '') for n in ET.fromstring(x).iter('node') if n.get('package') == pkg] if x else []
    return hashlib.md5('|'.join(re.sub(r'\d+', '#', t) for t in texts).encode()).hexdigest()
def front():
    m = re.search(r'mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/ }]+)', adb('shell', 'dumpsys', 'window'))
    return m.group(1) if m else ''
def launch(pkg):
    adb('shell', 'am', 'force-stop', pkg); adb('shell', 'monkey', '-p', pkg, '-c', 'android.intent.category.LAUNCHER', '1'); time.sleep(4)
report = ['# Button audit', '', 'Each button on the first screen, tapped from a fresh launch.', '']
for apk in sorted(os.listdir(APKS)):
    if not apk.endswith('.apk'): continue
    path = os.path.join(APKS, apk)
    pkg = sh(f'/usr/local/lib/android/sdk/build-tools/{BT}/aapt2', 'dump', 'packagename', path).strip()
    adb('uninstall', pkg); r = adb('install', '-r', '-g', path, timeout=300)
    report += [f'## {apk} ({pkg})', '']
    if 'Success' not in r: report += [f'Install failed: {r.strip()[:200]}', '']; continue
    launch(pkg); base = dump(); items = nodes(base, pkg)[:24]; base_sig = sig(base, pkg)
    d = os.path.join(OUT, apk[:-4]); os.makedirs(d, exist_ok=True)
    subprocess.run(f'adb exec-out screencap -p > "{d}/00-start.png"', shell=True)
    report.append(f'{len(items)} clickable items on the first screen.'); report.append('')
    report.append('| # | Button | Result |'); report.append('|---|---|---|')
    for i, (label, x, y) in enumerate(items, 1):
        launch(pkg); before = sig(dump(), pkg)
        adb('logcat', '-c'); adb('shell', 'input', 'tap', str(x), str(y)); time.sleep(2.5)
        alive = adb('shell', 'pidof', pkg).strip() != ''
        fg = front(); after = dump(); changed = sig(after, pkg) != before
        crash = adb('logcat', '-d', '-b', 'crash')
        if not alive or 'FATAL EXCEPTION' in crash: res = 'CRASH: ' + (re.search(r'(\w+(Exception|Error)[^\n]*)', crash).group(1)[:150] if re.search(r'(\w+(Exception|Error)[^\n]*)', crash) else 'process died')
        elif fg and pkg not in fg: res = f'opened another app/screen ({fg.split("/")[0]})'
        elif changed: res = 'screen changed'
        else: res = 'NO VISIBLE CHANGE (may be a toast or a dead button)'
        subprocess.run(f'adb exec-out screencap -p > "{d}/{i:02d}.png"', shell=True)
        report.append(f'| {i} | {label} | {res} |')
        adb('shell', 'input', 'keyevent', '4')
    report.append('')
open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(report))
print('\n'.join(report))
