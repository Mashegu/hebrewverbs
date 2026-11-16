from pathlib import Path
import ast

path = Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
s = path.read_text(encoding='utf-8')

old_version = "value = json.dumps([PROMPT_VERSION, req.section, req.topic.strip(), req.level], ensure_ascii=False)"
new_version = "value = json.dumps([PROMPT_VERSION + ('-roots-binyanim-v1' if req.section == 'roots' else ''), req.section, req.topic.strip(), req.level], ensure_ascii=False)"
old_prompt = "    if section == 'verbs':\n        item_spec += ("
new_prompt = '''    if section == 'roots':
        item_spec += (
            ' ROOTS SECTION STRICT FORMAT: Return only genuine Modern Hebrew VERB INFINITIVES '
            'derived from the same three-letter root; do not include nouns, adjectives, '
            'conjugated forms or duplicate infinitives. Do not invent non-existent verbs. '
            'For each entry, grammar must include root (three Hebrew consonants without niqqud), '
            'binyan (one of exactly: paal, nifal, piel, pual, hifil, hufal, hitpael), '
            'and partOfSpeech exactly verb. '
            'Only include an infinitive if its root, binyan and meaning are linguistically valid. '
            'Use the dictionary infinitive with accurate niqqud in entry.he. '
            'A binyan without an attested infinitive should be omitted, not fabricated. '
            'Set topic.he to the three-letter Hebrew root WITHOUT niqqud, '
            'not the original infinitive. '
            'Translate each infinitive accurately into ru, uk and en. '
            'If the requested verb is from a root with few attested infinitives, return fewer entries. '
        )
    if section == 'verbs':
        item_spec += ('''

old_validate = "    if section == 'verbs':\n        slots = [('present', 11), ('past', 9), ('future', 9), ('imperative', 4)]"
new_validate = '''    if section == 'roots':
        valid_binyanim = {'paal', 'nifal', 'piel', 'pual', 'hifil', 'hufal', 'hitpael'}
        valid_entries = [item for item in items if isinstance(item, dict)
                         and isinstance(item.get('grammar'), dict)
                         and item['grammar'].get('binyan') in valid_binyanim
                         and item['grammar'].get('partOfSpeech') == 'verb']
        if not valid_entries:
            raise ValueError('Roots response has no verified binyan infinitives')
    if section == 'verbs':
        slots = [('present', 11), ('past', 9), ('future', 9), ('imperative', 4)]'''

pairs = [(old_version,new_version,'версия кеша только для roots'),
         (old_prompt,new_prompt,'инструкция roots'),
         (old_validate,new_validate,'проверка биньянов roots')]
for old,new,label in pairs:
    if s.count(old) != 1:
        raise SystemExit('СТОП: не найден точный участок: '+label+'. Файл не изменён.')
    s=s.replace(old,new,1)
try:
    ast.parse(s)
except SyntaxError as e:
    raise SystemExit('СТОП: ошибка синтаксиса: '+str(e))
path.write_text(s,encoding='utf-8')
print('OK: изменены только инструкции/проверка roots и версия кеша roots. Остальные разделы не изменены; резервных копий нет.')
print('Для вступления изменений в силу потребуется перезапуск службы API.')
