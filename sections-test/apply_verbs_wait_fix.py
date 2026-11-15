#!/usr/bin/env python3
"""Extend only the verbs AI request deadlines; no backups or DB changes."""
from pathlib import Path

path = Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
src = path.read_text(encoding='utf-8')
old_client = 'client = AsyncOpenAI(api_key=key, timeout=25.0, max_retries=0)'
old_wait = 'return await asyncio.wait_for(_generate_verbsdb(req, cache_key, client), timeout=29.0)'
new_client = 'client = AsyncOpenAI(api_key=key, timeout=180.0, max_retries=0)'
new_wait = 'return await asyncio.wait_for(_generate_verbsdb(req, cache_key, client), timeout=190.0)'

if new_client in src and new_wait in src:
    print('OK: verbs AI waiting limits already extended; no changes needed')
    raise SystemExit(0)
if src.count(old_client) != 1 or src.count(old_wait) != 1:
    raise SystemExit('STOP: expected original timeout lines not found exactly once; file unchanged')
# The AsyncOpenAI client is shared by paid generation; use a verbs-only client
# to preserve timeout behavior of examples and reading.
old_block = "if req.section == 'verbs':\n            return await asyncio.wait_for(_generate_verbsdb(req, cache_key, client), timeout=29.0)"
new_block = "if req.section == 'verbs':\n            verbs_client = AsyncOpenAI(api_key=key, timeout=180.0, max_retries=0)\n            return await asyncio.wait_for(_generate_verbsdb(req, cache_key, verbs_client), timeout=190.0)"
if src.count(old_block) != 1:
    raise SystemExit('STOP: verbs branch not found exactly once; file unchanged')
updated = src.replace(old_block, new_block, 1)
compile(updated, str(path), 'exec')
path.write_text(updated, encoding='utf-8')
print('OK: verbs AI may wait up to 190 s; examples/reading unchanged; no backup')
