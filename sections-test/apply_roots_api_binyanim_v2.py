from pathlib import Path
import ast

path = Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
s = path.read_text(encoding='utf-8')

changes = [
    (
        "value = json.dumps([PROMPT_VERSION, req.section, req.topic.strip(), req.level], ensure_ascii=False)",
        "value = json.dumps([PROMPT_VERSION + ('-roots-binyanim-v2' if req.section == 'roots' else ''), req.section, req.topic.strip(), req.level], ensure_ascii=False)",
        "ключ кеша roots"
    ),
    (
        "    if section == 'verbs':\n        item_spec += (",
        """    if section == 'roots':
        item_spec += (
            ' ROOTS: Return only attested Modern Hebrew verb infinitives sharing the same '
            'three-consonant root. No nouns, adjectives, participles, or conjugated forms. '
            'Each entry.grammar MUST contain binyan exactly one of '
            'paal, nifal, piel, pual, hifil, hufal, hitpael; '
            'root as three Hebrew consonants without vowel points; '
            'partOfSpeech as verb. Include only genuinely attested infinitives; '
            'do not fabricate an infinitive for a passive binyan or to fill seven patterns. '
            'Each entry.he must be the correct dictionary infinitive with niqqud, '
            'and ru, uk, en must accurately translate that infinitive. '
            'Set topic.he to the root (three consonants, without niqqud). '
            'Omit doubtful forms and binyan labels. '
        )
    if section == 'verbs':
        item_spec += (""",
        "инструкция roots"
    ),
    (
        "    if section == 'verbs':\n        slots = [('present', 11), ('past', 9), ('future', 9), ('imperative', 4)]",
        """    if section == 'roots':
        allowed = {'paal', 'nifal', 'piel', 'pual', 'hifil', 'hufal', 'hitpael'}
        for item in items:
            grammar = item.get('grammar') if isinstance(item, dict) else None
            if not isinstance(grammar, dict) or grammar.get('binyan') not in allowed:
                raise ValueError('Roots entry missing valid grammar.binyan')
            if grammar.get('partOfSpeech') != 'verb':
                raise ValueError('Roots entry must be a verb')
    if section == 'verbs':
        slots = [('present', 11), ('past', 9), ('future', 9), ('imperative', 4)]""",
        "валидация roots"
    )
]

for old, new, label in changes:
    if s.count(new) == 1:
        continue
    if s.count(old) != 1:
        raise SystemExit('СТОП: не найден точный участок (' + label + '). Файл не изменён.')
    s = s.replace(old, new, 1)

ast.parse(s)
if s == path.read_text(encoding='utf-8'):
    print('OK: исправление уже установлено. Файл не изменён.')
else:
    path.write_text(s, encoding='utf-8')
    print('OK: обновлены только инструкция, проверка и кеш roots. Без резервных копий.')
print('После установки нужен отдельный перезапуск API.')
