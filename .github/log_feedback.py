#!/usr/bin/env python3
"""Build the SQL that records feedback a tester sent outside Beta Lane (text, call, email), so every piece of feedback
lives in one place with where it came from. The tester's words are stored exactly as sent; the channel, when it was
received, who logged it and what was done go in the record's source line. Usage: env vars below -> feedback.sql"""
import os, re
def q(s): return "'" + str(s).replace("'", "''") + "'"
partner = os.environ['PARTNER'].strip(); at = os.environ['AT'].strip()
assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', at), 'AT must look like 2026-11-15T21:44:00Z'
kind = os.environ.get('KIND', 'idea'); assert kind in ('bug', 'idea', 'love', 'confusing')
app = re.sub(r'[^a-z0-9-]', '', os.environ.get('APP', 'general').lower())[:40] or 'general'
text = os.environ['TEXT'].strip()[:4000]; source = os.environ['SOURCE'].strip()[:200]
assert len(text) >= 3 and source
code = f"(SELECT beta_code FROM partners WHERE name = {q(partner)} AND beta_code IS NOT NULL LIMIT 1)"
open('feedback.sql', 'w').write(
    f"INSERT INTO beta_feedback (code, at, app, kind, rating, text, device) SELECT {code}, {q(at)}, {q(app)}, {q(kind)}, 0, {q(text)}, {q(source)} "
    f"WHERE {code} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM beta_feedback WHERE code = {code} AND at = {q(at)} AND text = {q(text)});\n")
print(open('feedback.sql').read())
