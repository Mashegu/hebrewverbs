#!/usr/bin/env python3
"""Change only Examples AI generator and Examples + click handling. No backup."""
from pathlib import Path
import re
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
start=s.find('async function examplesAiGenerate(query){')
end=s.find("window.addEventListener('click',function(e){if(!document.body.classList.contains('independent-examples-mode'))return;",start)
if start<0 or end<0: raise SystemExit('STOP: Examples function boundaries not found; no changes')
old=s[start:end]
if '/* examples-single-current-v1 */' in old:
 print('OK: already installed; no changes');raise SystemExit(0)
required=['/* examples-parallel-v1 */','Promise.all(order.map(async function(tense)','examplesAiSpinner(true)','examplesAiSpinner(false)',"var order=['present','past','future','imperative']"]
if any(x not in old for x in required):raise SystemExit('STOP: unexpected Examples version; no changes')
click=s[end:]
needle="if(t.closest('#alwaysAiCodeAdd')){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();"
if click.count(needle)!=1:raise SystemExit('STOP: Examples plus handler not unique; no changes')
new='''/* examples-single-current-v1 */
 var examplesAiReady=null;
 async function examplesAiGenerate(query){
  if(examplesAiBusy)return;
  var rec=match(query),data=rec&&rec.data||{},inf=data.infinitive||{};
  var order=['present','past','future','imperative'],forms={};
  order.forEach(function(t){forms[t]=(Array.isArray(data[t])?data[t]:[]).map(function(r){return r&&r.he||'';}).filter(Boolean);});
  if(order.some(function(t){return !forms[t].length;})){
   examplesAiNotice('Для автоматических примеров необходимо полное спряжение выбранного глагола.');return;
  }
  examplesAiReady=null;examplesAiBusy=true;examplesAiSpinner(true);
  examplesAiNotice('AI создаёт примеры…');
  try{
   var names={present:'наст.',past:'прош.',future:'буд.',imperative:'повел.'};
   var hint=order.map(function(t){return names[t]+' '+forms[t].slice(0,2).join(',');}).join('; ');
   var topic=('Глагол '+(inf.he||query)+'. Дай примеры: настоящее, прошедшее, будущее, повелительное. Формы: '+hint).slice(0,120);
   var response=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'examples',topic:topic,level:'beginner'}),cache:'no-store'});
   if(!response.ok){
    var detail='';try{var err=await response.json();detail=err&&err.detail||'';}catch(_){}
    throw Error('HTTP '+response.status+(typeof detail==='string'&&detail?': '+detail:''));
   }
   var result=await response.json(),items=result&&result.sentences;
   if(!Array.isArray(items))throw Error('Ответ ИИ не содержит предложений');
   var used={},rows=[];
   order.forEach(function(t){
    var found=items.find(function(r){
     if(!r||!['he','ru','uk','en'].every(function(k){return typeof r[k]==='string'&&r[k].trim();}))return false;
     var key=examplesAiWords(r.he).join(' ');
     return !used[key]&&examplesAiMatches(r.he,forms[t]);
    });
    if(found){used[examplesAiWords(found.he).join(' ')]=true;rows.push({he:found.he,ru:found.ru,uk:found.uk,en:found.en});}
   });
   if(rows.length!==4)throw Error('ИИ вернул '+rows.length+' из 4 проверенных форм. Повторите попытку.');
   if(!document.body.classList.contains('independent-examples-mode')||!el('verbSearch')||el('verbSearch').value.trim()!==query)return;
   examplesAiReady={query:query,rows:rows};
   examplesAiNotice('Готово. Нажмите +, чтобы открыть четыре примера.');
  }catch(error){examplesAiNotice('Не удалось подготовить примеры: '+(error&&error.message||error));}
  finally{examplesAiBusy=false;examplesAiSpinner(false);}
 }
 '''
replacement="if(examplesAiBusy)return;if(examplesAiReady&&examplesAiReady.query===(el('verbSearch')?.value.trim()||current)){var ready=examplesAiReady;examplesAiReady=null;current=ready.query;render(ready.rows);displayed=true;return;}"
updated=s[:start]+new+s[end:].replace(needle,needle+replacement,1)
if updated.count('/* examples-single-current-v1 */')!=1:raise SystemExit('STOP: patch validation failed')
if updated[:start]!=s[:start]:raise SystemExit('STOP: unexpected change')
p.write_text(updated,encoding='utf-8')
print('OK: Examples now uses one AI request; + opens prepared examples; other sections unchanged; no backup')
