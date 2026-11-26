"""Shared HebrewVerbs AI API. Standalone; does not modify the live frontend."""
import os
import json
import logging
import sqlite3
import threading
import hashlib
import asyncio
import unicodedata
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
    test_namespace: Literal['test20261124', 'analogtest20261125'] | None = None
    binyan: Literal['paal','nifal','piel','pual','hifil','hufal','hitpael'] | None = None
    root: str | None = Field(default=None, max_length=8)

# All translations are generated in a single API call, regardless of UI language.
CONFIG = {
    'reading': {'kind': 'sentences', 'count': 10, 'description': 'One coherent Modern Hebrew reading story.'},
    'verbs': {'kind': 'forms', 'count': 33, 'description': 'Complete conjugation for the requested verb and relevant binyan: past, present, future and imperative where grammatical. Include person, gender, number and tense in each form.'},
    'prepositions': {'kind': 'forms', 'count': None, 'description': 'Complete standard pronominal inflections of the requested Hebrew preposition, with person, gender and number.'},
    'words': {'kind': 'forms', 'count': None, 'description': 'Grammatically applicable noun/adjective inflections for the requested word; do not invent inapplicable forms.'},
    'examples': {'kind': 'sentences', 'count': 10, 'description': 'Ten distinct, natural Hebrew example sentences for the requested word or construction.'},
    'roots': {'kind': 'entries', 'count': None, 'description': 'All and only lexically attested Modern Hebrew binyanim for the requested root, with their correctly pointed infinitives and precise distinct meanings where warranted.'},
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
PROMPT_VERSION = 'hebrew-roots-attested-only-v5'


def _cache_key(req):
    value = json.dumps([PROMPT_VERSION + ('-verbsdb-v1' if req.section == 'verbs' else ''), req.section, req.topic.strip(), req.level, *(["binyan-v7-root-normalized" if req.section == "verbs" else "binyan-v3-clean", req.binyan, req.root] if req.test_namespace and req.section in ("verbs", "roots") else []), *([req.test_namespace] if req.test_namespace else [])], ensure_ascii=False)
    if req.section == 'verbs' and req.test_namespace in ('test20261124', 'analogtest20261125'):
        value += ':academy-minimal-v2'
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
    if expected is not None and (not (1 <= len(items) <= 10) if section == 'examples' else (len(items) not in (9, 10) if section == 'reading' else len(items) != expected)):
        raise ValueError(f'Expected {expected} {kind}; received {len(items)}')
    if len(items) > 80:
        raise ValueError('Too many items')
    if section == 'roots':
        allowed = {'paal', 'nifal', 'piel', 'pual', 'hifil', 'hufal', 'hitpael'}
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Invalid root entry')
            grammar = item.get('grammar')
            if not isinstance(grammar, dict) or grammar.get('binyan') not in allowed:
                raise ValueError('Invalid root binyan')
            if grammar['binyan'] in seen:
                raise ValueError('Duplicate root binyan')
            seen.add(grammar['binyan'])
            if not isinstance(item.get('he'), str) or not item['he'].startswith('ל'):
                raise ValueError('Root entry is not a Hebrew infinitive')
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
    if section == 'roots':
        item_spec += (
            ' TASK: identify the Hebrew root and examine ALL SEVEN binyanim independently: '
            'paal, nifal, piel, pual, hifil, hufal, hitpael. '
            'This is a FILTERING task, NOT a task to fill seven slots. '
            'Return ONLY binyanim with a genuinely attested Modern Hebrew verb of this exact root '
            'and a genuinely used infinitive. The output may contain any number from ONE to SEVEN. '
            'Never include a binyan merely because its morphological pattern could theoretically be formed. '
            'For every candidate, check actual lexical usage and its dictionary meaning BEFORE inclusion. '
            'If you cannot confidently substantiate that verb and its infinitive as genuinely used, OMIT it. '
            'Especially scrutinize passive pual and hufal: a passive participle or finite passive form '
            'does NOT establish that a standalone infinitive is used. Omit these binyanim if the '
            'infinitive is only hypothetical or unattested. '
            'Each entry.he must be an actual fully pointed Hebrew INFINITIVE beginning with ל, '
            'never a participle, finite form, or root alone. '
            'Each entry.grammar must contain binyan (one of paal,nifal,piel,pual,hifil,hufal,hitpael) '
            'and root (the same unpointed Hebrew root in every entry). '
            'At most ONE entry per binyan; do not duplicate infinitives. '
            'For each included infinitive supply its own precise, idiomatic ru, uk and en meaning, '
            'not a mechanically copied translation of another binyan. '
            'Prefer one or two words per translation, without synonym lists. '
            'Check that the translation corresponds to this EXACT binyan and not another derivative. '
            'For example, the hifil of נשא, לְהַשִּׂיא, can mean to marry off; '
            'it does not simply mean to carry. '
            'Before returning JSON, review every included binyan for attestation, '
            'real infinitive, correct niqqud and semantic accuracy. '
            'If uncertain, exclude rather than invent. '
            'Return only the existing API JSON format, not JavaScript. '
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

# Curated paradigms for the regression root סגר. Other verbs retain AI generation.
_TEST_PARADIGMS = {
    'לִסְגֹּר': ('paal', 'סוֹגֵר סוֹגֶרֶת סוֹגְרִים סוֹגְרוֹת', 'סָגַרְתִּי סָגַרְתָּ סָגַרְתְּ סָגַר סָגְרָה סָגַרְנוּ סְגַרְתֶּם סְגַרְתֶּן סָגְרוּ', 'אֶסְגֹּר תִּסְגֹּר תִּסְגְּרִי יִסְגֹּר תִּסְגֹּר נִסְגֹּר תִּסְגְּרוּ תִּסְגֹּרְנָה יִסְגְּרוּ', 'סְגֹר סִגְרִי סִגְרוּ סְגֹרְנָה'),
    'לְהִסָּגֵר': ('nifal', 'נִסְגָּר נִסְגֶּרֶת נִסְגָּרִים נִסְגָּרוֹת', 'נִסְגַּרְתִּי נִסְגַּרְתָּ נִסְגַּרְתְּ נִסְגַּר נִסְגְּרָה נִסְגַּרְנוּ נִסְגַּרְתֶּם נִסְגַּרְתֶּן נִסְגְּרוּ', 'אֶסָּגֵר תִּסָּגֵר תִּסָּגְרִי יִסָּגֵר תִּסָּגֵר נִסָּגֵר תִּסָּגְרוּ תִּסָּגַרְנָה יִסָּגְרוּ', 'הִסָּגֵר הִסָּגְרִי הִסָּגְרוּ הִסָּגַרְנָה'),
    'לְסַגֵּר': ('piel', 'מְסַגֵּר מְסַגֶּרֶת מְסַגְּרִים מְסַגְּרוֹת', 'סִגַּרְתִּי סִגַּרְתָּ סִגַּרְתְּ סִגֵּר סִגְּרָה סִגַּרְנוּ סִגַּרְתֶּם סִגַּרְתֶּן סִגְּרוּ', 'אֲסַגֵּר תְּסַגֵּר תְּסַגְּרִי יְסַגֵּר תְּסַגֵּר נְסַגֵּר תְּסַגְּרוּ תְּסַגֵּרְנָה יְסַגְּרוּ', 'סַגֵּר סַגְּרִי סַגְּרוּ סַגֵּרְנָה'),
    'לְהַסְגִּיר': ('hifil', 'מַסְגִּיר מַסְגִּירָה מַסְגִּירִים מַסְגִּירוֹת', 'הִסְגַּרְתִּי הִסְגַּרְתָּ הִסְגַּרְתְּ הִסְגִּיר הִסְגִּירָה הִסְגַּרְנוּ הִסְגַּרְתֶּם הִסְגַּרְתֶּן הִסְגִּירוּ', 'אַסְגִּיר תַּסְגִּיר תַּסְגִּירִי יַסְגִּיר תַּסְגִּיר נַסְגִּיר תַּסְגִּירוּ תַּסְגֵּרְנָה יַסְגִּירוּ', 'הַסְגֵּר הַסְגִּירִי הַסְגִּירוּ הַסְגֵּרְנָה'),
}


def _bare_he(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))


def _normalize_lexical_root(s):
    # Remove only recognized root separators; reject other characters below.
    root = ''.join(c for c in _bare_he(s) if not c.isspace() and c not in '-־–—·.\u200e\u200f')
    if not (2 <= len(root) <= 4 and all('א' <= c <= 'ת' for c in root)):
        logger.warning('Invalid lexical root: raw=%r normalized=%r', s, root)
        raise ValueError('Invalid lexical root')
    return root


def _pointed(s):
    return unicodedata.normalize('NFC', s.strip())


async def _generate_test_verbs(req, cache_key, client):
    model = os.getenv('HEBREWVERBS_TEST_VERB_MODEL', 'gpt-4.1')
    def obj(properties):
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    string = {'type':'string'}
    identity_schema = obj({'root':string,'binyan':{'type':'string','enum':['paal','nifal','piel','pual','hifil','hufal','hitpael']},'infinitive':obj({k:string for k in TRANSLATIONS})})
    forms_schema = obj({k:{'type':'array','items':string} for k in _VERB_SLOTS})
    labels_schema = obj({k:{'type':'array','items':obj({lang:string for lang in ('ru','uk','en')})} for k in _VERB_SLOTS})
    async def ask(instruction, payload, schema, name):
        response = await client.chat.completions.create(
            model=model, temperature=0, response_format={'type':'json_schema','json_schema':{'name':name,'strict':True,'schema':schema}},
            max_tokens=6500, messages=[{'role':'system','content':instruction},
            {'role':'user','content':json.dumps(payload,ensure_ascii=False)}])
        choice = response.choices[0]
        if getattr(choice.message, 'refusal', None) or choice.finish_reason != 'stop' or not choice.message.content:
            raise ValueError('Incomplete structured response: '+name)
        return json.loads(choice.message.content)
    # Exact multilingual aliases are resolved before the AI identity request.
    academy = [{'root': 'כתב', 'binyan': 'קל', 'infinitive': 'לִכְתֹּב', 'forms': {'present': [['כּוֹתֵב'], ['כּוֹתֶבֶת'], ['כּוֹתְבִים'], ['כּוֹתְבוֹת']], 'past': [['כָּתַבְתִּי'], ['כָּתַבְתָּ'], ['כָּתַבְתְּ'], ['כָּתַב'], ['כָּתְבָה'], ['כָּתַבְנוּ'], ['כְּתַבְתֶּם'], ['כְּתַבְתֶּן'], ['כָּתְבוּ']], 'future': [['אֶכְתֹּב'], ['תִּכְתֹּב'], ['תִּכְתְּבִי'], ['יִכְתֹּב'], ['תִּכְתֹּב'], ['נִכְתֹּב'], ['תִּכְתְּבוּ'], ['תִּכְתֹּבְנָה'], ['יִכְתְּבוּ']], 'imperative': [['כְּתֹב'], ['כִּתְבִי'], ['כִּתְבוּ'], ['כְּתֹבְנָה']]}, 'status': 'PENDING'}, {'root': 'שמר', 'binyan': 'קל', 'infinitive': 'לִשְׁמֹר', 'forms': {'present': [['שׁוֹמֵר'], ['שׁוֹמֶרֶת'], ['שׁוֹמְרִים'], ['שׁוֹמְרוֹת']], 'past': [['שָׁמַרְתִּי'], ['שָׁמַרְתָּ'], ['שָׁמַרְתְּ'], ['שָׁמַר'], ['שָׁמְרָה'], ['שָׁמַרְנוּ'], ['שְׁמַרְתֶּם'], ['שְׁמַרְתֶּן'], ['שָׁמְרוּ']], 'future': [['אֶשְׁמֹר'], ['תִּשְׁמֹר'], ['תִּשְׁמְרִי'], ['יִשְׁמֹר'], ['תִּשְׁמֹר'], ['נִשְׁמֹר'], ['תִּשְׁמְרוּ'], ['תִּשְׁמֹרְנָה'], ['יִשְׁמְרוּ']], 'imperative': [['שְׁמֹר'], ['שִׁמְרִי'], ['שִׁמְרוּ'], ['שְׁמֹרְנָה']]}, 'status': 'PENDING'}, {'root': 'למד', 'binyan': 'קל', 'infinitive': 'לִלְמֹד', 'forms': {'present': [['לוֹמֵד', 'לָמֵד'], ['לוֹמֶדֶת', 'לְמֵדָה'], ['לוֹמְדִים', 'לְמֵדִים'], ['לוֹמְדוֹת', 'לְמֵדוֹת']], 'past': [['לָמַדְתִּי'], ['לָמַדְתָּ'], ['לָמַדְתְּ'], ['לָמַד'], ['לָמְדָה'], ['לָמַדְנוּ'], ['לְמַדְתֶּם'], ['לְמַדְתֶּן'], ['לָמְדוּ']], 'future': [['אֶלְמַד'], ['תִּלְמַד'], ['תִּלְמְדִי'], ['יִלְמַד'], ['תִּלְמַד'], ['נִלְמַד'], ['תִּלְמְדוּ'], ['תִּלְמַדְנָה'], ['יִלְמְדוּ']], 'imperative': [['לְמַד'], ['לִמְדִי'], ['לִמְדוּ'], ['לְמַדְנָה']]}, 'status': 'PENDING'}, {'root': 'שלח', 'binyan': 'קל', 'infinitive': 'לִשְׁלֹחַ', 'forms': {'present': [['שׁוֹלֵחַ'], ['שׁוֹלַחַת'], ['שׁוֹלְחִים'], ['שׁוֹלְחוֹת']], 'past': [['שָׁלַחְתִּי'], ['שָׁלַחְתָּ'], ['שָׁלַחְתְּ', 'שָׁלַחַתְּ'], ['שָׁלַח'], ['שָׁלְחָה'], ['שָׁלַחְנוּ'], ['שְׁלַחְתֶּם'], ['שְׁלַחְתֶּן'], ['שָׁלְחוּ']], 'future': [['אֶשְׁלַח'], ['תִּשְׁלַח'], ['תִּשְׁלְחִי'], ['יִשְׁלַח'], ['תִּשְׁלַח'], ['נִשְׁלַח'], ['תִּשְׁלְחוּ'], ['תִּשְׁלַחְנָה'], ['יִשְׁלְחוּ']], 'imperative': [['שְׁלַח'], ['שִׁלְחִי'], ['שִׁלְחוּ'], ['שְׁלַחְנָה']]}, 'status': 'PENDING'}, {'root': 'שמע', 'binyan': 'קל', 'infinitive': 'לִשְׁמֹעַ', 'forms': {'present': [['שׁוֹמֵעַ'], ['שׁוֹמַעַת'], ['שׁוֹמְעִים'], ['שׁוֹמְעוֹת']], 'past': [['שָׁמַעְתִּי'], ['שָׁמַעְתָּ'], ['שָׁמַעְתְּ', 'שָׁמַעַתְּ'], ['שָׁמַע'], ['שָׁמְעָה'], ['שָׁמַעְנוּ'], ['שְׁמַעְתֶּם'], ['שְׁמַעְתֶּן'], ['שָׁמְעוּ']], 'future': [['אֶשְׁמַע'], ['תִּשְׁמַע'], ['תִּשְׁמְעִי'], ['יִשְׁמַע'], ['תִּשְׁמַע'], ['נִשְׁמַע'], ['תִּשְׁמְעוּ'], ['תִּשְׁמַעְנָה'], ['יִשְׁמְעוּ']], 'imperative': [['שְׁמַע'], ['שִׁמְעִי'], ['שִׁמְעוּ'], ['שְׁמַעְנָה']]}, 'status': 'PENDING'}]
    academy_aliases = (
        ('писать','писати','write','to write','לכתוב'),
        ('хранить','сохранять','зберігати','keep','to keep','preserve','to preserve','לשמור'),
        ('учиться','вчитися','навчатися','learn','to learn','study','to study','ללמוד'),
        ('посылать','отправлять','посилати','надсилати','send','to send','לשלוח'),
        ('слышать','чути','hear','to hear','לשמוע'),
    )
    meanings = (('писать','писати','to write'),('хранить','зберігати','to keep'),('учиться','вчитися','to learn'),('посылать','надсилати','to send'),('слышать','чути','to hear'))
    q = _bare_he(req.topic.strip()).casefold()
    exact_input = next(((r, m) for r, aliases, m in zip(academy, academy_aliases, meanings)
                        if q in (*aliases, _bare_he(r['infinitive']))
                        and (not req.binyan or req.binyan == 'paal')
                        and (not req.root or _normalize_lexical_root(req.root) == r['root'])), None)
    if exact_input:
        r, m = exact_input
        target = {'root':r['root'], 'binyan':'paal', 'infinitive':dict(zip(TRANSLATIONS, (r['infinitive'], *m)))}
    else:
        target = await ask(
            'Resolve the intended Modern Hebrew verb by meaning. Identify its root, then binyan, then fully pointed infinitive. Return JSON root (2 to 4 consecutive Hebrew letters, no separators, e.g. סגר), binyan (paal,nifal,piel,pual,hifil,hufal,hitpael), infinitive (he,ru,uk,en). Respect supplied root and binyan. Do not conjugate yet.',
            {'topic':req.topic,'root':req.root,'binyan':req.binyan},identity_schema,'verb_identity')
    inf = target['infinitive']
    _text_fields(inf,'infinitive')
    root = _normalize_lexical_root(target['root'])
    binyan = target['binyan']
    if binyan not in ('paal','nifal','piel','pual','hifil','hufal','hitpael'):
        raise ValueError('Invalid lexical binyan')
    if req.root and _normalize_lexical_root(req.root) != root or req.binyan and req.binyan != binyan:
        raise ValueError('Requested root or binyan mismatch')
    if binyan == 'paal':
        reference = next((r for r in academy if r['root'] == root and _bare_he(inf['he']) in (_bare_he(r['infinitive']), academy_aliases[academy.index(r)][-1])), None)
        if reference:
            inf['he'] = reference['infinitive']
    if not inf['he'].startswith('ל') or _bare_he(inf['he']) == inf['he']:
        raise ValueError('Expected pointed infinitive')
    if req.binyan and _pointed(req.topic) != _pointed(inf['he']) and not (exact_input and _bare_he(req.topic) == _bare_he(inf['he'])):
        raise ValueError('Requested infinitive mismatch')
    # Curated paradigms are authoritative only for exact lexical matches.
    aliases = {'закрывать':'לִסְגֹּר','закрыть':'לִסְגֹּר','закрываться':'לְהִסָּגֵר'}
    known = aliases.get(req.topic.strip().lower()) if not req.binyan and not req.root else None
    if known:
        inf['he'] = known
        root, binyan = 'סגר', _TEST_PARADIGMS[known][0]
    paradigm = next((v for k,v in _TEST_PARADIGMS.items() if _pointed(k)==_pointed(inf['he']) and v[0]==binyan),None)
    order = {'present':4,'past':9,'future':9,'imperative':4}
    identity = {'root':root,'binyan':binyan,'infinitive':inf}
    if req.test_namespace in ('test20261124', 'analogtest20261125') and binyan == 'paal':
        # Local Academy transcriptions: exact matches only while PENDING.
        exact = next((r for r in academy if r['root'] == root and _bare_he(r['infinitive']) == _bare_he(inf['he'])), None)
        if exact:
            identity['academy_reference'] = exact
        else:
            identity['academy_references'] = [r for r in academy if r['status'] == 'APPROVED']
    if req.test_namespace in ('test20261124', 'analogtest20261125') and identity.get('academy_reference'):
        reference = identity['academy_reference']
        inf['he'] = reference['infinitive']
        hebrew = {t:[variants[0] for variants in reference['forms'][t]] for t in order}
    elif paradigm:
        hebrew = {t:w.split() for t,w in zip(order,paradigm[1:])}
    else:
        instruction = ('Conjugate ONLY the locked lexical identity. Return JSON arrays of pointed Hebrew strings only. Present: masculine singular,feminine singular,masculine plural,feminine plural. Past and future: I,you m,you f,he,she,we,you m plural,you f plural,they. Imperative: you m,you f,you m plural,you f plural. Use — for genuinely inapplicable imperative slots. Never substitute a different binyan. No pronouns or translations. If candidate_analogs are supplied, use only morphologically compatible patterns as experimental guidance; never copy their root or assume their niqqud is correct.')
        if req.test_namespace in ('test20261124', 'analogtest20261125'):
            instruction += ' For an exact academy_reference, use its infinitive and listed forms, choosing one listed variant per slot. For approved academy_references only, select compatible patterns separately by tense; do not infer future vowels from the root alone. Preserve lexical identity and check all niqqud before answering.'
        hebrew = await ask(instruction,identity,forms_schema,'verb_forms')
        hebrew = await ask(instruction+' Audit the candidate for root, binyan, person and niqqud; return corrected arrays.',{'identity':identity,'candidate':hebrew},forms_schema,'verb_audit')
    for tense,n in order.items():
        rows=hebrew[tense]
        if not isinstance(rows,list) or len(rows)!=n:
            raise ValueError('Invalid '+tense+' count')
        for word in rows:
            if not isinstance(word,str) or not (tense=='imperative' and word=='—') and (not _bare_he(word) or not all('א' <= c <= 'ת' for c in _bare_he(word)) or word==_bare_he(word)):
                raise ValueError('Invalid pointed form')
    ms,fs,mp,fp=map(_bare_he,hebrew['present'])
    if not mp.endswith('ים') or not fp.endswith('ות') or len({w.startswith('מ') for w in (ms,fs,mp,fp)})!=1:
        raise ValueError('Mixed present patterns')
    hebrew['present']=[hebrew['present'][j] for j in (0,1,0,1,0,1,2,2,3,2,3)]
    labels=await ask('Translate the supplied fixed Hebrew forms according to their grammatical slots and lexical meaning. Return JSON present,past,future,imperative arrays of objects ru,uk,en only. Present order I m,I f,you m,you f,he,she,we,you m plural,you f plural,they m,they f. Past/future order I,you m,you f,he,she,we,you m plural,you f plural,they. Imperative order you m,you f,you m plural,you f plural. For — use — in all languages. Never change Hebrew.' + (' Independently verify Russian, Ukrainian and English for meaning, tense, gender and number; correct errors before returning; omit personal pronouns.' if req.test_namespace in ('test20261124', 'analogtest20261125') else ''),{'identity':identity,'forms':hebrew},labels_schema,'verb_translations')
    forms=[]
    for tense,slots in _VERB_SLOTS.items():
        if len(labels[tense])!=len(slots):
            raise ValueError('Invalid translation count')
        for i,(person,gender,number) in enumerate(slots):
            row={**labels[tense][i],'he':hebrew[tense][i]}
            _text_fields(row,tense)
            forms.append({**{k:row[k] for k in TRANSLATIONS},'grammar':{'tense':tense,'slot':i,'person':person,'gender':gender,'number':number}})
    data=validate_result({'section':'verbs','topic':inf,'forms':forms,'level':req.level,'root':root,'binyan':binyan},'verbs')
    with _db() as conn:
        conn.execute('INSERT OR REPLACE INTO cache(cache_key,result) VALUES (?,?)',(cache_key,json.dumps(data,ensure_ascii=False)))
    return data


async def _generate_verbsdb(req, cache_key, client):
    if req.test_namespace:
        return await _generate_test_verbs(req, cache_key, client)
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
    model = os.getenv("HEBREWVERBS_TEST_VERB_MODEL", "gpt-4.1") if req.test_namespace else os.getenv("HEBREWVERBS_AI_MODEL", "gpt-4o-mini")
    response = await client.chat.completions.create(
        model=model,
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
        need = 4 if req.test_namespace and tense == 'present' else len(slots)
        if not isinstance(rows, list) or len(rows) != need:
            if not req.test_namespace and (not isinstance(rows, list) or len(rows) > need):
                raise ValueError(f'Invalid {tense} rows')
            missing[tense] = {'have':len(rows) if isinstance(rows,list) else 0,'need':need}
    if missing:
        repair = await client.chat.completions.create(
            model=model,
            temperature=0.1, response_format={'type':'json_object'}, max_tokens=5500,
            messages=[
                {'role':'system','content':(
                    'Return a JSON object containing ONLY the requested tense arrays, each '
                    'with its FULL required number of rows, in the exact grammatical order. '
                    'Each row needs he,ru,uk,en; correct Hebrew niqqud. ' +
                    ('Present order: masculine singular,feminine singular,masculine plural,feminine plural. ' if req.test_namespace else 'Present order: I m,I f,you m,you f,he,she,we,you m plural,you f plural,they m,they f. ') +
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

async def _generate_paid(req: GenerateRequest, cache_key: str):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise HTTPException(status_code=503, detail='AI service not configured')
    client = AsyncOpenAI(api_key=key, timeout=90.0 if req.section == 'examples' or (req.test_namespace and req.section == 'roots') else 25.0, max_retries=0)
    try:
        if req.section == 'verbs':
            verbs_client = AsyncOpenAI(api_key=key, timeout=180.0, max_retries=0)
            return await asyncio.wait_for(_generate_verbsdb(req, cache_key, verbs_client), timeout=360.0 if req.test_namespace else 190.0)
        response = await client.chat.completions.create(
            model=os.getenv('HEBREWVERBS_TEST_VERB_MODEL', 'gpt-4.1') if req.test_namespace and req.section == 'roots' else os.getenv('HEBREWVERBS_AI_MODEL', 'gpt-4o-mini'),
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
    except (OpenAIError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError, asyncio.TimeoutError):
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
