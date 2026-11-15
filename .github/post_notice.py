#!/usr/bin/env python3
"""SQL for a Beta Lane notice (news shown to every active tester). Runs once; the same title isn't posted twice."""
import os, re
def q(s): return "'" + str(s).replace("'", "''") + "'"
title = os.environ['TITLE'].strip()[:120]; body = os.environ.get('BODY', '').strip()[:1000]
app = re.sub(r'[^a-z0-9-]', '', os.environ.get('APP', ''))[:40]; at = os.environ['AT'].strip()
assert title and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', at)
open('notice.sql', 'w').write(
    "CREATE TABLE IF NOT EXISTS beta_notices (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, title TEXT, body TEXT, app TEXT, active INTEGER DEFAULT 1);\n"
    f"INSERT INTO beta_notices (at, title, body, app, active) SELECT {q(at)}, {q(title)}, {q(body)}, {q(app)}, 1 WHERE NOT EXISTS (SELECT 1 FROM beta_notices WHERE title = {q(title)});\n")
print(open('notice.sql').read())
