#!/usr/bin/env python3
"""Parallelize only AI example tense requests. No backups, API or verbsDB edits."""
from pathlib import Path
import re

path = Path('/var/www/hebrewverbs-clean/verbs.html')
src = path.read_text(encoding='utf-8')
start = src.find('async function examplesAiGenerate(query){')
end = src.find("window.addEventListener('click'", start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit('STOP: Examples AI function not found; no changes')
old = src[start:end]
if '/* examples-parallel-v1 */' in old:
    print('OK: parallel Examples AI already installed; no changes')
    raise SystemExit(0)
if 'examplesAiSpinner(true)' not in old or 'examplesAiSpinner(false)' not in old:
    raise SystemExit('STOP: expected Examples spinner not found; no changes')
if "section:'examples'" not in old or "var order=['present','past','future','imperative']" not in old:
    raise SystemExit('STOP: Examples AI structure differs; no changes')
if old.count('for(var i=0;i<order.length;i++){') != 1 or old.count("if(!document.body.classList.contains('independent-examples-mode')") != 1:
    raise SystemExit('STOP: expected sequential loop not found exactly once; no changes')
head, tail = old.split('for(var i=0;i<order.length;i++){', 1)
match = re.search(r"\n\s*if\(!document\.body\.classList\.contains\('independent-examples-mode'\)", tail)
if not match:
    raise SystemExit('STOP: end of generation loop not found; no changes')
remaining = tail[match.start():]
new_loop = '''/* examples-parallel-v1 */
   var labels={present:'настоящем времени',past:'прошедшем времени',future:'будущем времени',imperative:'повелительном наклонении'};
   var results=await Promise.all(order.map(async function(tense){
    var lastError='';
    for(var attempt=0;attempt<5;attempt++){
     var sample=forms[tense].slice(attempt===0?0:attempt===1?3:attempt===2?4:attempt===3?7:8,attempt===0?3:attempt===1?6:attempt===2?7:attempt===3?10:11).join(', ');
     var topic=('Глагол '+(inf.he||query)+': '+labels[tense]+'; '+sample+'; 5 предложений с огласовками, переводы ru uk en').slice(0,120);
     try{
      var response=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'examples',topic:topic,level:'beginner'}),cache:'no-store'});
      if(!response.ok){lastError='HTTP '+response.status;continue;}
      var result=await response.json(),items=result&&result.sentences;
      if(!Array.isArray(items)){lastError='Ответ AI не содержит предложений';continue;}
      var candidates=items.filter(function(r){return r&&['he','ru','uk','en'].every(function(k){return typeof r[k]==='string'&&r[k].trim();})&&examplesAiMatches(r.he,forms[tense]);});
      if(candidates.length)return {tense:tense,candidates:candidates};
      lastError='Нет проверенной формы глагола';
     }catch(e){lastError=String(e&&e.message||e);}
    }
    throw Error('Не получен пример для '+labels[tense]+': '+lastError);
   }));
   results.forEach(function(result){
    var found=result.candidates.find(function(r){return !used[examplesAiWords(r.he).join(' ')];});
    if(!found)throw Error('Нет уникального примера для '+labels[result.tense]);
    rows[result.tense]={he:found.he,ru:found.ru,uk:found.uk,en:found.en};
    used[examplesAiWords(found.he).join(' ')]=true;
   });'''
updated = src[:start] + head + new_loop + remaining + src[end:]
if updated.count('/* examples-parallel-v1 */') != 1:
    raise SystemExit('STOP: unexpected marker count; no changes')
# Verify only the expected function changes.
assert updated[:start] == src[:start]
assert updated[updated.find("window.addEventListener('click'", start):] == src[end:]
path.write_text(updated, encoding='utf-8')
print('OK: Examples AI tense requests parallelized; verbs, verbsDB, API, Firebase unchanged; no backup')
