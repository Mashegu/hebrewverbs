from pathlib import Path
import ast

path = Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
original = path.read_text(encoding='utf-8')
s = original

old_cache = "PROMPT_VERSION + ('-verbsdb-v1' if req.section == 'verbs' else '')"
new_cache = "PROMPT_VERSION + ('-verbsdb-v1' if req.section == 'verbs' else '-roots-binyanim-v3' if req.section == 'roots' else '')"

old_instruction = "    if section == 'verbs':\n        item_spec += ("
new_instruction = """    if section == 'roots':
        item_spec += (
            ' ROOTS TASK: Return only genuinely attested Hebrew VERB INFINITIVES '
            'that share the requested three-consonant Hebrew root. '
            'For EACH entry set grammar.partOfSpeech to verb, '
            'grammar.binyan to EXACTLY one of: paal, nifal, piel, pual, hifil, hufal, hitpael, '
            'and grammar.root to the Hebrew root without vowel points. '
            'The entry.he must be an actual Hebrew dictionary infinitive with correct niqqud. '
            'Provide exact ru, uk, en translations of that infinitive. '
            'Do not include finite forms, adjectives, nouns or participles. '
            'Do not invent forms for binyanim that lack an attested infinitive. '
            'Include fewer than 15 entries when appropriate. '
            'Set topic.he to the Hebrew root without vowel points. '
        )
    if section == 'verbs':
        item_spec += ("""

for old, new, label in ((old_cache, new_cache, 'ключ кеша'), (old_instruction, new_instruction, 'инструкция roots')):
    if new in s:
        continue
    if s.count(old) != 1:
        raise SystemExit('СТОП: не найден точный участок (' + label + '). Файл не изменён.')
    s = s.replace(old, new, 1)

ast.parse(s)
if s == original:
    print('OK: исправление уже присутствует; файл не изменён.')
else:
    path.write_text(s, encoding='utf-8')
    print('OK: обновлены только инструкция roots и версия кеша roots. Без резервных копий.')
print('Для применения изменений потребуется перезапуск API отдельной командой.')
