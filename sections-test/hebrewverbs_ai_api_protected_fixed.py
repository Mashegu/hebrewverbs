"""Shared HebrewVerbs AI API. Standalone; does not modify the live frontend."""
import os
import json
import logging
import sqlite3
import threading
import hashlib
from exercise_templates import EXERCISE_TEMPLATES

# Independent rotation for each exercise category.
_exercise_template_positions = {category: 0 for category in EXERCISE_TEMPLATES}
_exercise_template_lock = threading.Lock()

def _next_exercise_template(category):
    with _exercise_template_lock:
        templates = EXERCISE_TEMPLATES[category]
        index = _exercise_template_positions[category]
        _exercise_template_positions[category] = (index + 1) % len(templates)
        return index, templates[index]

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

load_dotenv('/opt/hebrewverbs-ai/.env')
logger = logging.getLogger('hebrewverbs.ai')
app = FastAPI(title='HebrewVerbs AI API')

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mashegu.github.io"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


Section = Literal['reading', 'verbs', 'prepositions', 'words', 'examples', 'roots']
Level = Literal['beginner', 'intermediate', 'advanced']

class GenerateRequest(BaseModel):
    section: Section
    topic: str = Field(min_length=1, max_length=120)
    level: Level = 'beginner'

# All translations are generated in a single API call, regardless of UI language.
CONFIG = {
    'reading': {'kind': 'sentences', 'count': 10, 'description': 'One coherent Modern Hebrew reading story.'},
    'verbs': {'kind': 'forms', 'count': 33, 'description': 'Complete conjugation for the requested verb and relevant binyan: past, present, future and imperative where grammatical. Include person, gender, number and tense in each form.'},
    'prepositions': {'kind': 'forms', 'count': None, 'description': 'Complete standard pronominal inflections of the requested Hebrew preposition, with person, gender and number.'},
    'words': {'kind': 'forms', 'count': None, 'description': 'Grammatically applicable noun/adjective inflections for the requested word; do not invent inapplicable forms.'},
    'examples': {'kind': 'sentences', 'count': 10, 'description': 'Ten distinct, natural Hebrew example sentences for the requested word or construction.'},
    'roots': {'kind': 'entries', 'count': None, 'description': 'Up to 15 genuine words derived from the requested Hebrew root, with binyan where applicable. Never invent derivatives to reach a quota.'},
}

TRANSLATIONS = ('he', 'ru', 'uk', 'en')

# Shared across processes through SQLite. Reservations are never refunded: failed
# requests also consume quota, preventing repeated paid retries.
DB_PATH = Path(os.getenv('HEBREWVERBS_AI_DB', '/opt/hebrewverbs-ai/ai_usage.sqlite3'))
DAILY_IP_LIMIT = 366
MONTHLY_GLOBAL_LIMIT = 11000
MAX_INFLIGHT = 2
_gate = threading.BoundedSemaphore(MAX_INFLIGHT)


def _db():
    conn = sqlite3.connect(str(DB_PATH), timeout=15, isolation_level=None)
    conn.execute('PRAGMA busy_timeout=15000')
    conn.execute('CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, month TEXT NOT NULL, ip TEXT NOT NULL)')
    conn.execute('CREATE INDEX IF NOT EXISTS usage_day_ip ON usage(day, ip)')
    conn.execute('CREATE INDEX IF NOT EXISTS usage_month ON usage(month)')
    conn.execute('CREATE TABLE IF NOT EXISTS cache (cache_key TEXT PRIMARY KEY, result TEXT NOT NULL)')
    return conn


# Increment when generation instructions change, so older cached texts are not reused.
PROMPT_VERSION = 'hebrew-proofread-v3'


def _cache_key(req):
    value = json.dumps([PROMPT_VERSION + ('-verbsdb-v1' if req.section == 'verbs' else ''), req.section, req.topic.strip(), req.level], ensure_ascii=False)
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _cached(cache_key):
    with _db() as conn:
        row = conn.execute('SELECT result FROM cache WHERE cache_key=?', (cache_key,)).fetchone()
    return json.loads(row[0]) if row else None


def _reserve(ip):
    now = datetime.now(timezone.utc)
    day, month = now.strftime('%Y-%m-%d'), now.strftime('%Y-%m')
    conn = _db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT COUNT(*) FROM usage WHERE month=?', (month,)).fetchone()[0] >= MONTHLY_GLOBAL_LIMIT:
            conn.execute('ROLLBACK')
            raise HTTPException(status_code=429, detail='Monthly AI generation limit reached')
        if conn.execute('SELECT COUNT(*) FROM usage WHERE day=? AND ip=?', (day, ip)).fetchone()[0] >= DAILY_IP_LIMIT:
            conn.execute('ROLLBACK')
            raise HTTPException(status_code=429, detail='Daily AI generation limit reached')
        conn.execute('INSERT INTO usage(day, month, ip) VALUES (?, ?, ?)', (day, month, ip))
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    finally:
        conn.close()




def _text_fields(obj, label):
    if not isinstance(obj, dict):
        raise ValueError(f'{label}: expected object')
    for key in TRANSLATIONS:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise ValueError(f'{label}: missing {key}')

def validate_result(data, section):
    if not isinstance(data, dict):
        raise ValueError('Expected JSON object')
    if data.get('section') != section:
        raise ValueError('Section mismatch')
    _text_fields(data.get('topic'), 'topic')
    kind = CONFIG[section]['kind']
    items = data.get(kind)
    if not isinstance(items, list) or not items:
        raise ValueError(f'Missing or empty {kind}')
    expected = CONFIG[section]['count']
    if expected is not None and (len(items) not in (9, 10) if section in ('reading', 'examples') else len(items) != expected):
        raise ValueError(f'Expected {expected} {kind}; received {len(items)}')
    if len(items) > 80:
        raise ValueError('Too many items')
    if section == 'verbs':
        slots = [('present', 11), ('past', 9), ('future', 9), ('imperative', 4)]
        expected_slots = [(tense, slot) for tense, count in slots for slot in range(count)]
        actual_slots = []
        for item in items:
            grammar = item.get('grammar') if isinstance(item, dict) else None
            if not isinstance(grammar, dict):
                raise ValueError('Verb form missing grammar')
            slot = grammar.get('slot')
            if type(slot) is not int:
                raise ValueError('Verb form missing integer grammar.slot')
            actual_slots.append((grammar.get('tense'), slot))
        missing = [x for x in expected_slots if x not in actual_slots]
        extra = [x for x in actual_slots if x not in expected_slots]
        duplicates = [x for x in set(actual_slots) if actual_slots.count(x) > 1]
        if missing or extra or duplicates:
            raise ValueError(f'Invalid verb slots: missing={missing}, extra={extra}, duplicates={duplicates}')
        items.sort(key=lambda item: expected_slots.index((item['grammar']['tense'], item['grammar']['slot'])))
    for i, item in enumerate(items):
        _text_fields(item, f'{kind}[{i}]')
        if kind == 'sentences':
            words = item.get('words')
            if not isinstance(words, list) or not words:
                raise ValueError(f'{kind}[{i}]: missing words')
            for j, word in enumerate(words):
                _text_fields(word, f'{kind}[{i}].words[{j}]')
                if not isinstance(word.get('pos'), str) or not word['pos'].strip():
                    raise ValueError(f'{kind}[{i}].words[{j}]: missing pos')
        else:
            if not isinstance(item.get('grammar'), dict):
                raise ValueError(f'{kind}[{i}]: missing grammar object')
    return data


def _instructions(section, level):
    config = CONFIG[section]
    kind = config['kind']
    count = config['count']
    count_instruction = f'Exactly {count} items.' if count else 'Include all applicable forms; omit non-existent forms.'
    item_spec = (
        'Each sentence must have he, ru, uk, en and a nonempty words array; '
        'each word has he, ru, uk, en and pos. '
        'Allowed pos: noun, adjective, numeral, pronoun, verb, adverb, '
        'preposition, conjunction, other.'
        if kind == 'sentences' else
        'Each item must have he, ru, uk, en and grammar (a JSON object with relevant grammatical labels).'
    )
    if section == 'verbs':
        item_spec += (
            ' For verb conjugation return exactly 33 forms: '
            'present 11, past 9, future 9, imperative 4. '
            'Return exactly 33 entries in forms, never fewer or more. '
            'For every form set grammar.person to 1, 2 or 3 as a string; '
        'grammar.gender to m, f or an empty string; '
        'grammar.number to s or p. '
        'Use an empty gender for first-person past and future forms. '
        'Use grammar.tense exactly present, past, future or imperative. '
        'Use grammar.slot as a zero-based integer within its tense. '
        'Use this exact order of grammatical slots: '
            'present (11): ani masculine, ani feminine, ata, at, hu, hi, anachnu, atem, aten, hem, hen; '
            'past (9): ani, ata, at, hu, hi, anachnu, atem, aten, hem; '
            'future (9): ani, ata, at, hu, hi, anachnu, atem, aten, hem; '
            'imperative (4): ata, at, atem, aten. '
            'Every slot must have he, ru, uk, en and grammar. '
            'Set grammar.tense to present, past, future or imperative. Set grammar.slot to a ZERO-BASED integer: present 0-10, past 0-8, future 0-8, imperative 0-3. Never use one-based numbering. '
            'For shared Hebrew forms repeat the same correct form in each required slot. '
            'Do not omit slots even when forms are identical. '
            'Before responding count 11+9+9+4=33 entries. '
            'Each form must contain he, ru, uk, en and grammar. '
            'Grammar must contain tense, person, gender, number. '
            'Use accurate Modern Hebrew with niqqud. '
            'Do not invent forms or translations. '
        )
    return (
        'You are a meticulous Modern Hebrew language teaching content creator. '
        'Use accurate Hebrew niqqud (vowel points) on Hebrew words. '
        'Ensure idiomatic, accurate Russian, Ukrainian and English translations. '
        'Never add invented grammatical forms or incorrect root derivatives. '
        f'Section: {section}. Level: {level}. Task: {config["description"]} '
        f'{count_instruction} '
        'Return only a JSON object, no markdown. '
        f'Keys: section (exactly "{section}"), level (string), '
        'topic (object with he, ru, uk, en), '
        f'{kind} (array). {item_spec} '
        'Before finalizing, silently proofread EVERY Hebrew field and its translations, '
        'including topic, sentences, word entries, conjugated forms and root derivatives. '
        'Verify standard Modern Hebrew spelling and correct niqqud for every Hebrew word, '
        'including verb patterns, prefixes, articles, prepositions and suffixes. '
        'Verify grammar, tense, person, gender and number agreement, syntax and natural '
        'Modern Hebrew phrasing appropriate to the requested level. '
        'Verify each Russian, Ukrainian and English translation against its exact Hebrew '
        'source: preserve meaning, negation, tense, person, gender, number and nuance; '
        'use natural, grammatically correct language in each translation. '
        'For sentences, verify that every words-array entry actually occurs in its '
        'sentence in the appropriate form, has accurate he/ru/uk/en equivalents, '
        'and a correct part-of-speech label. '
        'For forms and entries, check grammatical labels and reject fabricated or '
        'nonstandard forms. Correct any detected error before returning the result. '
        'Do not output proofreading notes or claims of verification. '
        'Check all required keys and the item count before responding.'
    )

@app.get('/health')
async def health():
    return {'status': 'ok'}

@app.post('/api/ai/generate')
async def generate(req: GenerateRequest, request: Request):
    # Use the socket peer, never a user-controlled X-Forwarded-For header.
    # Behind nginx, configure a trusted proxy strategy before public launch.
    ip = request.client.host if request.client else 'unknown'
    cache_key = _cache_key(req)
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    if not _gate.acquire(blocking=False):
        raise HTTPException(status_code=429, detail='AI server busy; try later')
    try:
        # Recheck cache after obtaining the gate.
        cached = _cached(cache_key)
        if cached is not None:
            return cached
        _reserve(ip)
        return await _generate_paid(req, cache_key)
    finally:
        _gate.release()


def _missing_verb_slots(data):
    expected = [
        (tense, slot)
        for tense, count in (
            ('present', 11),
            ('past', 9),
            ('future', 9),
            ('imperative', 4),
        )
        for slot in range(count)
    ]
    forms = data.get('forms', [])
    if not isinstance(forms, list):
        raise ValueError('Invalid verb forms')
    found = []
    for form in forms:
        if not isinstance(form, dict):
            raise ValueError('Invalid verb form')
        grammar = form.get('grammar')
        if not isinstance(grammar, dict):
            raise ValueError('Missing verb grammar')
        slot = grammar.get('slot')
        if type(slot) is not int:
            raise ValueError('Invalid grammar.slot')
        key = (grammar.get('tense'), slot)
        if key not in expected:
            continue
        if key in found:
            raise ValueError(f'Duplicate verb slot: {key}')
        found.append(key)
    return [key for key in expected if key not in found]


# The original manual verbsDB request uses only four translated text fields.
# Convert its fixed 33 rows to the legacy API format without asking AI for grammar.
_VERB_SLOTS = {
    'present': [('1','m','s'),('1','f','s'),('2','m','s'),('2','f','s'),('3','m','s'),('3','f','s'),('1','','p'),('2','m','p'),('2','f','p'),('3','m','p'),('3','f','p')],
    'past': [('1','','s'),('2','m','s'),('2','f','s'),('3','m','s'),('3','f','s'),('1','','p'),('2','m','p'),('2','f','p'),('3','','p')],
    'future': [('1','','s'),('2','m','s'),('2','f','s'),('3','m','s'),('3','f','s'),('1','','p'),('2','m','p'),('2','f','p'),('3','','p')],
    'imperative': [('2','m','s'),('2','f','s'),('2','m','p'),('2','f','p')],
}

async def _generate_verbsdb(req, cache_key, client):
    prompt = (
        'Fill the existing Hebrew conjugation template for the verb: ' + req.topic + '. '
        'Return ONLY one JSON object with keys infinitive, present, past, future, imperative. '
        'This is the data inside the working manual verbsDB assignment, not a new format. '
        'Each row and infinitive must have exactly he, ru, uk, en, all nonempty strings. '
        'he is correctly conjugated Modern Hebrew WITH accurate niqqud; ru Russian, uk Ukrainian, en English. '
        'Translations are natural verb forms WITHOUT pronouns, since the site already displays pronouns. '
        'Do NOT include grammar, person, pronoun, personHe or pronounHe fields. '
        'Do not invent or reorder pronouns. Use the requested verb, its real infinitive and correct binyan. '
        'Present exactly 11 rows in this order: I masculine, I feminine, you masculine singular, '
        'you feminine singular, he, she, we, you masculine plural, you feminine plural, '
        'they masculine, they feminine. '
        'Past exactly 9 rows: I, you masculine singular, you feminine singular, he, she, we, '
        'you masculine plural, you feminine plural, they. '
        'Future exactly the same 9 slots as past. '
        'Imperative exactly 4 rows: you masculine singular, you feminine singular, '
        'you masculine plural, you feminine plural. '
        'For shared Hebrew forms repeat the correct form. '
        'Use standard correct Hebrew niqqud, and accurate natural ru/uk/en translations. '
        'Return valid JSON, not JavaScript, not markdown, with exactly 11+9+9+4=33 rows.'
    )
    response = await client.chat.completions.create(
        model=os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
        temperature=0.2,
        response_format={'type': 'json_object'},
        max_tokens=12000,
        messages=[{'role':'system','content':prompt}, {'role':'user','content':req.topic}],
    )
    verb = json.loads(response.choices[0].message.content)
    if not isinstance(verb, dict):
        raise ValueError('Expected verbsDB object')
    infinitive = verb.get('infinitive')
    _text_fields(infinitive, 'infinitive')
    if not infinitive['he'].startswith('ל'):
        raise ValueError('Expected Hebrew infinitive')
    forms = []
    for tense, slots in _VERB_SLOTS.items():
        rows = verb.get(tense)
        if not isinstance(rows, list) or len(rows) != len(slots):
            raise ValueError(f'Expected {len(slots)} {tense} forms')
        for i, (row, (person, gender, number)) in enumerate(zip(rows, slots)):
            _text_fields(row, f'{tense}[{i}]')
            forms.append({**{k:row[k] for k in TRANSLATIONS},
                'grammar':{'tense':tense,'slot':i,'person':person,'gender':gender,'number':number}})
    data = validate_result({'section':'verbs','topic':{k:infinitive[k] for k in TRANSLATIONS},'forms':forms}, 'verbs')
    data['level'] = req.level
    with _db() as conn:
        conn.execute('INSERT OR REPLACE INTO cache(cache_key, result) VALUES (?, ?)',
                     (cache_key, json.dumps(data, ensure_ascii=False)))
    return data


async def _generate_paid(req: GenerateRequest, cache_key: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise HTTPException(status_code=503, detail='AI service not configured')
    client = AsyncOpenAI(api_key=key, timeout=60.0, max_retries=0)
    try:
        if req.section == 'verbs':
            return await _generate_verbsdb(req, cache_key, client)
        response = await client.chat.completions.create(
            model=os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
            temperature=0.3,
            response_format={'type': 'json_object'},
            max_tokens=12000,
            messages=[
                {'role': 'system', 'content': _instructions(req.section, req.level)},
                {'role': 'user', 'content': f'Topic: {req.topic}'},
            ],
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        if req.section == 'verbs':
            allowed = {
                (tense, slot)
                for tense, count in (
                    ('present', 11),
                    ('past', 9),
                    ('future', 9),
                    ('imperative', 4),
                )
                for slot in range(count)
            }

            collected = {}
            for form in data.get('forms', []):
                if not isinstance(form, dict):
                    continue
                grammar = form.get('grammar')
                if not isinstance(grammar, dict):
                    continue
                slot = grammar.get('slot')
                if type(slot) is not int:
                    continue
                key = (grammar.get('tense'), slot)
                if key in allowed and key not in collected:
                    collected[key] = form

            for attempt in range(6):
                missing = [key for key in sorted(allowed) if key not in collected]
                if not missing:
                    break

                batch = missing[:6]
                repair_response = await client.chat.completions.create(
                    model=os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
                    temperature=0.2,
                    response_format={'type': 'json_object'},
                    max_tokens=3500,
                    messages=[
                        {
                            'role': 'system',
                            'content': (
                                'You are a precise Modern Hebrew conjugation assistant. '
                                'Return JSON containing a forms array. '
                                'Generate ONLY the requested grammatical slots. '
                                'Each form needs he, ru, uk, en and grammar. '
                                'Grammar must contain tense, slot, person, gender, number. '
                                'Use accurate Hebrew niqqud. '
                                'Return each requested slot with its exact tense and zero-based slot number.'
                            ),
                        },
                        {
                            'role': 'user',
                            'content': json.dumps({
                                'topic': req.topic,
                                'missing_slots': [
                                    {'tense': tense, 'slot': slot}
                                    for tense, slot in batch
                                ],
                                'existing_forms': list(collected.values()),
                            }, ensure_ascii=False),
                        },
                    ],
                )

                repair = json.loads(repair_response.choices[0].message.content)
                additions = repair.get('forms', [])
                if not isinstance(additions, list):
                    continue

                for form in additions:
                    if not isinstance(form, dict):
                        continue
                    grammar = form.get('grammar')
                    if not isinstance(grammar, dict):
                        continue
                    slot = grammar.get('slot')
                    if type(slot) is not int:
                        continue
                    key = (grammar.get('tense'), slot)
                    if key not in batch or key in collected:
                        continue
                    if not all(
                        isinstance(form.get(lang), str) and form[lang].strip()
                        for lang in ('he', 'ru', 'uk', 'en')
                    ):
                        continue
                    collected[key] = form

            missing = [key for key in allowed if key not in collected]
            if missing:
                raise ValueError(f'Repair still missing verb slots: {missing}')

            order = (
                [('present', i) for i in range(11)]
                + [('past', i) for i in range(9)]
                + [('future', i) for i in range(9)]
                + [('imperative', i) for i in range(4)]
            )
            data['forms'] = [collected[key] for key in order]
        data = validate_result(data, req.section)
        data['level'] = req.level
        with _db() as conn:
            conn.execute('INSERT OR REPLACE INTO cache(cache_key, result) VALUES (?, ?)', (cache_key, json.dumps(data, ensure_ascii=False)))
        return data
    except (OpenAIError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        logger.exception('AI generation or validation failed: section=%s', req.section)
        raise HTTPException(status_code=502, detail='AI generation failed validation')


# Isolated morphology-exercise endpoints. Existing generation routes are unchanged.
EXERCISE_CATEGORIES = ('nouns','adjectives','numerals','pronouns','verbs','adverbs','prepositions','conjunctions')
EXERCISE_POS = ('noun','adjective','numeral','pronoun','verb','adverb','preposition','conjunction','particle','article','other')

class ExerciseCreateRequest(BaseModel):
    category: Literal['nouns','adjectives','numerals','pronouns','verbs','adverbs','prepositions','conjunctions']
    level: Level = 'beginner'

class ExerciseCheckRequest(BaseModel):
    category: Literal['nouns','adjectives','numerals','pronouns','verbs','adverbs','prepositions','conjunctions']
    level: Level = 'beginner'
    translation: dict
    options: list[str] = Field(min_length=6, max_length=6)
    correct: int = Field(ge=0, le=5)
    selected: int = Field(ge=0, le=5)
    correctAnswers: list[int] = Field(min_length=1, max_length=2)

class MorphologyAutoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=30000)

@app.post("/api/ai/morphology/auto")
async def morphology_auto(req: MorphologyAutoRequest):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    client = AsyncOpenAI(api_key=key, timeout=90.0, max_retries=0)
    response = await client.chat.completions.create(
        model=os.getenv("HEBREWVERBS_AI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=5000,
        messages=[
            {"role": "system", "content": "Follow the supplied Hebrew morphology exercise instructions exactly. Return one JSON object only."},
            {"role": "user", "content": req.prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)
