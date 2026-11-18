"""SQLite storage routes for HebrewVerbs.

Integration in hebrewverbs_ai_api_protected.py after app creation:
    from verb_storage_api import router as storage_router
    app.include_router(storage_router)

Configure VERB_STORAGE_SECRET (persistent random 32+ chars) in the service
environment. API must be served over HTTPS for GitHub Pages cookie access.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/storage', tags=['verb-storage'])
DB_PATH = Path(os.environ.get('VERB_STORAGE_DB', '/opt/hebrewverbs-ai/verb_storage.sqlite3'))
SECRET = os.environ.get('VERB_STORAGE_SECRET', '')
COOKIE = 'hv_storage_session'
MAX_AGE = 365 * 24 * 3600
MAX_VERBS = 100
MAX_EXAMPLES = 20
ALLOWED_ORIGINS = {'https://mashegu.github.io', 'http://159.223.31.89'}


def signer():
    if len(SECRET) < 32:
        raise HTTPException(503, 'Server session secret is not configured')
    return URLSafeTimedSerializer(SECRET, salt='hebrewverbs-storage-v1')


@contextmanager
def connect():
    db = sqlite3.connect(str(DB_PATH), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=10000')
    try:
        yield db
    finally:
        db.close()


def check_origin(request):
    if request.headers.get('origin') not in ALLOWED_ORIGINS:
        raise HTTPException(403, 'Origin not allowed')


def get_user(request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, 'Session required')
    try:
        user_id = signer().loads(token, max_age=MAX_AGE)
        if type(user_id) is not int or user_id < 1:
            raise ValueError('Invalid user')
    except (BadSignature, ValueError, TypeError):
        raise HTTPException(401, 'Invalid session')
    return user_id


def set_cookie(request, response, user_id):
    # Secure, cross-site cookie. HTTPS is mandatory for this to work.
    response.set_cookie(COOKIE, signer().dumps(user_id), max_age=MAX_AGE,
                        httponly=True, secure=True, samesite='none',
                        path='/api/storage')


class VerbIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    record: dict


class ExamplesIn(BaseModel):
    examples: list = Field(max_length=MAX_EXAMPLES)


@router.post('/session')
def session(request: Request, response: Response):
    check_origin(request)
    try:
        user_id = get_user(request)
        with connect() as db:
            if db.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
                set_cookie(request, response, user_id)
                return {'ok': True}
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    with connect() as db:
        with db:
            user_id = db.execute('INSERT INTO users DEFAULT VALUES').lastrowid
    set_cookie(request, response, user_id)
    return {'ok': True}


@router.get('/verbs')
def list_verbs(request: Request):
    user_id = get_user(request)
    with connect() as db:
        rows = db.execute('SELECT verb_key, conjugation_json FROM verbs WHERE user_id=? ORDER BY id DESC',
                          (user_id,)).fetchall()
    return {'verbs': [{'key': row['verb_key'], 'record': json.loads(row['conjugation_json'])}
                      for row in rows]}


@router.put('/verbs')
def save_verb(payload: VerbIn, request: Request):
    check_origin(request)
    user_id = get_user(request)
    data = json.dumps(payload.record, ensure_ascii=False)
    if len(data.encode('utf-8')) > 250_000:
        raise HTTPException(413, 'Verb record too large')
    with connect() as db:
        with db:
            db.execute('''INSERT INTO verbs(user_id, verb_key, conjugation_json)
                          VALUES(?,?,?) ON CONFLICT(user_id,verb_key)
                          DO UPDATE SET conjugation_json=excluded.conjugation_json''',
                       (user_id, payload.key, data))
            count = db.execute('SELECT count(*) FROM verbs WHERE user_id=?', (user_id,)).fetchone()[0]
            if count > MAX_VERBS:
                # FIFO until last_opened_at is added to the schema for true LRU.
                db.execute('''DELETE FROM verbs WHERE id IN (
                              SELECT id FROM verbs WHERE user_id=? AND verb_key<>?
                              ORDER BY created_at, id LIMIT ?)''',
                           (user_id, payload.key, count - MAX_VERBS))
    return {'ok': True}


@router.delete('/verbs/{verb_key}')
def delete_verb(verb_key: str, request: Request):
    check_origin(request)
    user_id = get_user(request)
    with connect() as db:
        with db:
            result = db.execute('DELETE FROM verbs WHERE user_id=? AND verb_key=?',
                                (user_id, verb_key))
    # SQLite foreign_keys=ON removes examples in the same transaction.
    return {'ok': True, 'removed': result.rowcount > 0}


@router.get('/verbs/{verb_key}/examples')
def read_examples(verb_key: str, request: Request):
    user_id = get_user(request)
    with connect() as db:
        row = db.execute('''SELECT e.examples_json FROM examples e
                            JOIN verbs v ON v.id=e.verb_id
                            WHERE v.user_id=? AND v.verb_key=?
                            ORDER BY e.id DESC LIMIT 1''',
                         (user_id, verb_key)).fetchone()
    return {'examples': json.loads(row['examples_json']) if row else []}


@router.put('/verbs/{verb_key}/examples')
def save_examples(verb_key: str, payload: ExamplesIn, request: Request):
    check_origin(request)
    user_id = get_user(request)
    data = json.dumps(payload.examples, ensure_ascii=False)
    if len(data.encode('utf-8')) > 250_000:
        raise HTTPException(413, 'Examples too large')
    with connect() as db:
        with db:
            verb = db.execute('SELECT id FROM verbs WHERE user_id=? AND verb_key=?',
                              (user_id, verb_key)).fetchone()
            if not verb:
                raise HTTPException(404, 'Verb not found')
            db.execute('DELETE FROM examples WHERE verb_id=?', (verb['id'],))
            db.execute('INSERT INTO examples(verb_id,examples_json) VALUES(?,?)',
                       (verb['id'], data))
    return {'ok': True}
