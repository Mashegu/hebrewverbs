"""Shared HebrewVerbs AI API. Standalone; does not modify the live frontend."""
import os
import json
import logging
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

load_dotenv('/opt/hebrewverbs-ai/.env')
logger = logging.getLogger('hebrewverbs.ai')
app = FastAPI(title='HebrewVerbs AI API')

Section = Literal['reading', 'verbs', 'prepositions', 'words', 'examples', 'roots']
Level = Literal['beginner', 'intermediate', 'advanced']

class GenerateRequest(BaseModel):
    section: Section
    topic: str = Field(min_length=1, max_length=120)
    level: Level = 'beginner'

# All translations are generated in a single API call, regardless of UI language.
CONFIG = {
    'reading': {'kind': 'sentences', 'count': 10, 'description': 'One coherent Modern Hebrew reading story.'},
    'verbs': {'kind': 'forms', 'count': None, 'description': 'Complete conjugation for the requested verb and relevant binyan: past, present, future and imperative where grammatical. Include person, gender, number and tense in each form.'},
    'prepositions': {'kind': 'forms', 'count': None, 'description': 'Complete standard pronominal inflections of the requested Hebrew preposition, with person, gender and number.'},
    'words': {'kind': 'forms', 'count': None, 'description': 'Grammatically applicable noun/adjective inflections for the requested word; do not invent inapplicable forms.'},
    'examples': {'kind': 'sentences', 'count': 10, 'description': 'Ten distinct, natural Hebrew example sentences for the requested word or construction.'},
    'roots': {'kind': 'entries', 'count': None, 'description': 'Up to 15 genuine words derived from the requested Hebrew root, with binyan where applicable. Never invent derivatives to reach a quota.'},
}

TRANSLATIONS = ('he', 'ru', 'uk', 'en')

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
    if expected is not None and len(items) != expected:
        raise ValueError(f'Expected {expected} {kind}; received {len(items)}')
    if len(items) > 80:
        raise ValueError('Too many items')
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
        'Check all required keys and the item count before responding.'
    )

@app.get('/health')
async def health():
    return {'status': 'ok'}

@app.post('/api/ai/generate')
async def generate(req: GenerateRequest):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise HTTPException(status_code=503, detail='AI service not configured')
    client = AsyncOpenAI(api_key=key, timeout=60.0, max_retries=0)
    try:
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
        data = validate_result(json.loads(raw), req.section)
        data['level'] = req.level
        return data
    except (OpenAIError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        logger.exception('AI generation or validation failed: section=%s', req.section)
        raise HTTPException(status_code=502, detail='AI generation failed validation')
