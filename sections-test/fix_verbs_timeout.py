#!/usr/bin/env python3
"""Patch only verb generation in the installed HebrewVerbs API; no backups."""
from pathlib import Path
import ast
p=Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
s=p.read_text(encoding='utf-8')
assert 'async def _generate_verbsdb(req, cache_key, client):' in s, 'Expected verb generator missing; no changes made'
assert "return await _generate_verbsdb(req, cache_key, client)" in s, 'Expected verb route missing; no changes made'
assert "client = AsyncOpenAI(api_key=key, timeout=60.0, max_retries=0)" in s, 'Unexpected client configuration; no changes made'
start=s.index('async def _generate_verbsdb(req, cache_key, client):')
end=s.index('\nasync def _generate_paid(',start)
replacement='''async def _generate_verbsdb(req, cache_key, client):
    prompt = (
        'Conjugate the requested Modern Hebrew verb into the existing manual verbsDB template. '
        'Return ONLY a JSON object with infinitive, present, past, future, imperative. '
        'Each infinitive and row must contain he, ru, uk, en as nonempty strings. '
        'Hebrew must have correct niqqud; translations must be accurate. '
        'Do not include grammar, pronouns, or JavaScript. '
        'Present 11 rows IN ORDER: I masculine, I feminine, you masculine singular, '
        'you feminine singular, he, she, we, you masculine plural, you feminine plural, '
        'they masculine, they feminine. '
        'Past 9 rows IN ORDER: I, you masculine, you feminine, he, she, we, '
        'you masculine plural, you feminine plural, they. '
        'Future 9 rows in the same order as past. '
        'Imperative 4 rows: you masculine, you feminine, you masculine plural, you feminine plural. '
        'Repeat identical Hebrew conjugations for distinct grammatical slots. '
        'Count all 33 rows before replying. Never omit a row.'
    )
    response = await client.chat.completions.create(
        model=os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
        temperature=0.1, response_format={'type':'json_object'}, max_tokens=10000,
        messages=[{'role':'system','content':prompt}, {'role':'user','content':req.topic}],
    )
    verb = json.loads(response.choices[0].message.content)
    if not isinstance(verb, dict):
        raise ValueError('Expected verbsDB object')
    infinitive = verb.get('infinitive')
    _text_fields(infinitive, 'infinitive')
    if not infinitive['he'].startswith('ל'):
        raise ValueError('Expected Hebrew infinitive')
    # One targeted repair, only for missing rows. Never pad with fabricated forms.
    missing = {}
    for tense, slots in _VERB_SLOTS.items():
        rows = verb.get(tense)
        if not isinstance(rows, list) or len(rows) > len(slots):
            raise ValueError(f'Invalid {tense} rows')
        if len(rows) < len(slots):
            missing[tense] = {'have':len(rows),'need':len(slots)}
    if missing:
        repair = await client.chat.completions.create(
            model=os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
            temperature=0.1, response_format={'type':'json_object'}, max_tokens=5500,
            messages=[
                {'role':'system','content':(
                    'Return a JSON object containing ONLY the requested tense arrays, each '
                    'with its FULL required number of rows, in the exact grammatical order. '
                    'Each row needs he,ru,uk,en; correct Hebrew niqqud. '
                    'Present order: I m,I f,you m,you f,he,she,we,you m plural,you f plural,they m,they f. '
                    'Past and future: I,you m,you f,he,she,we,you m plural,you f plural,they. '
                    'Imperative: you m,you f,you m plural,you f plural. '
                    'Never omit rows even when Hebrew forms repeat.'
                )},
                {'role':'user','content':json.dumps({'verb':req.topic,'infinitive':infinitive,'missing':missing},ensure_ascii=False)},
            ],
        )
        fixed=json.loads(repair.choices[0].message.content)
        if not isinstance(fixed,dict):
            raise ValueError('Invalid repair')
        for tense in missing:
            verb[tense]=fixed.get(tense)
    forms=[]
    for tense, slots in _VERB_SLOTS.items():
        rows=verb.get(tense)
        if not isinstance(rows,list) or len(rows)!=len(slots):
            raise ValueError(f'Expected {len(slots)} {tense} forms')
        for i,(row,(person,gender,number)) in enumerate(zip(rows,slots)):
            _text_fields(row,f'{tense}[{i}]')
            forms.append({**{k:row[k] for k in TRANSLATIONS},
                'grammar':{'tense':tense,'slot':i,'person':person,'gender':gender,'number':number}})
    data=validate_result({'section':'verbs','topic':{k:infinitive[k] for k in TRANSLATIONS},'forms':forms},'verbs')
    data['level']=req.level
    with _db() as conn:
        conn.execute('INSERT OR REPLACE INTO cache(cache_key, result) VALUES (?, ?)',
                     (cache_key,json.dumps(data,ensure_ascii=False)))
    return data
'''
s=s[:start]+replacement+s[end:]
s=s.replace('import hashlib\n','import hashlib\nimport asyncio\n',1)
s=s.replace("client = AsyncOpenAI(api_key=key, timeout=60.0, max_retries=0)","client = AsyncOpenAI(api_key=key, timeout=25.0, max_retries=0)",1)
s=s.replace('return await _generate_verbsdb(req, cache_key, client)','return await asyncio.wait_for(_generate_verbsdb(req, cache_key, client), timeout=29.0)',1)
s=s.replace('except (OpenAIError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):','except (OpenAIError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError, asyncio.TimeoutError):',1)
ast.parse(s)
p.write_text(s,encoding='utf-8')
print('OK: verbs-only patch applied, timeout 29 seconds, one repair attempt; no backup created')
