from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
a=s.find("    var sample=forms[tense].slice(0,6).join(")
b=s.find("\n   }\n   if(!document.body.classList.contains",a)
if a<0 or b<0:
    raise SystemExit('STOP: expected examples code not found; nothing changed')
replacement="    var found=null,lastError='';\n    for(var attempt=0;attempt<3&&!found;attempt++){\n     var sample=forms[tense].slice(attempt===0?0:attempt===1?3:0,attempt===0?4:attempt===1?7:8).join(', ');\n     var topic='Составь 5 коротких предложений на иврите с глаголом '+(inf.he||query)+'. Время: '+labels[tense]+'. Используй эти формы с огласовками: '+sample+'. Переводы ru, uk, en.';\n     try{\n      var response=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'examples',topic:topic,level:'beginner'}),cache:'no-store'});\n      if(!response.ok){lastError='HTTP '+response.status;continue;}\n      var result=await response.json(),items=result&&result.sentences;\n      if(!Array.isArray(items)){lastError='Ответ AI не содержит предложений';continue;}\n      found=items.find(function(r){return r&&['he','ru','uk','en'].every(function(k){return typeof r[k]==='string'&&r[k].trim();})&&examplesAiMatches(r.he,forms[tense])&&!used[examplesAiWords(r.he).join(' ')];});\n      if(!found)lastError='Нет проверенной формы глагола';\n     }catch(e){lastError=String(e&&e.message||e);}\n    }\n    if(!found)throw Error('Не получен пример для '+labels[tense]+': '+lastError);\n    rows[tense]={he:found.he,ru:found.ru,uk:found.uk,en:found.en};\n    used[examplesAiWords(found.he).join(' ')]=true;"
p.write_text(s[:a]+replacement+s[b:],encoding='utf-8')
print('OK: automatic examples retry fix; other sections unchanged; no backup')
