from pathlib import Path
import re
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
if '/* examples-ready-single-request-20261115 */' in s:
 print('OK: already installed');raise SystemExit
start=s.index(' // Automatic examples: only replaces the manual ChatGPT opening in this section.')
end=s.index(" window.addEventListener('click',function(e){if(!document.body.classList.contains('independent-examples-mode'))return;",start)
new=''' /* examples-ready-single-request-20261115 */
 var examplesAiBusy=false,examplesAiReady=null,examplesAiRun=0;
 function examplesAiNotice(message){
  var root=el('independentExamplesScreen');if(!root)return;
  render([]);var note=document.createElement('div');note.className='independent-note';
  note.textContent=message;root.appendChild(note);
 }
 function examplesAiWords(value){return String(value||'').normalize('NFKC').replace(/[\\u0591-\\u05c7]/g,'').match(/[\\u05d0-\\u05ea]+/g)||[];}
 function examplesAiMatches(sentence,forms){var words=examplesAiWords(sentence);return forms.some(function(form){var parts=examplesAiWords(form);return parts.length>0&&parts.some(function(part){return words.indexOf(part)!==-1;});});}
 async function examplesAiGenerate(query){
  if(examplesAiBusy)return;
  var rec=match(query),data=rec&&rec.data||{},inf=data.infinitive||{};
  var order=['present','past','future','imperative'],forms={};
  order.forEach(function(t){forms[t]=(Array.isArray(data[t])?data[t]:[]).map(function(r){return r&&r.he||'';}).filter(Boolean);});
  examplesAiReady=null;
  if(order.some(function(t){return !forms[t].length;})){examplesAiNotice('Для автоматических примеров необходимо полное спряжение выбранного глагола.');return;}
  var run=++examplesAiRun;examplesAiBusy=true;
  var ai=el('alwaysAiCodeAI');if(ai)ai.setAttribute('aria-busy','true');
  examplesAiNotice('AI создаёт примеры…');
  try{
   var names={present:'настоящее',past:'прошедшее',future:'будущее',imperative:'повелительное'};
   var hint=order.map(function(t){return names[t]+': '+forms[t].slice(0,4).join(', ');}).join('; ');
   var topic=('Глагол '+(inf.he||query)+'. Создай четыре коротких предложения с огласовками: настоящее, прошедшее, будущее, повелительное. Формы: '+hint+'. Для каждого переводы ru uk en.').slice(0,1200);
   var response=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'examples',topic:topic,level:'beginner'}),cache:'no-store'});
   if(!response.ok){var detail='';try{var error=await response.json();detail=error&&error.detail||'';}catch(_){}throw Error('HTTP '+response.status+(typeof detail==='string'&&detail?': '+detail:''));}
   var result=await response.json(),items=result&&result.sentences;
   if(!Array.isArray(items))throw Error('Ответ AI не содержит предложений');
   var used={},rows=[];
   order.forEach(function(t){
    var found=items.find(function(r){if(!r||!['he','ru','uk','en'].every(function(k){return typeof r[k]==='string'&&r[k].trim();}))return false;var key=examplesAiWords(r.he).join(' ');return !used[key]&&examplesAiMatches(r.he,forms[t]);});
    if(found){used[examplesAiWords(found.he).join(' ')]=true;rows.push({he:found.he,ru:found.ru,uk:found.uk,en:found.en});}
   });
   if(rows.length!==4)throw Error('ИИ вернул '+rows.length+' из 4 проверенных форм. Повторите попытку.');
   if(run!==examplesAiRun||!document.body.classList.contains('independent-examples-mode')||el('verbSearch')?.value.trim()!==query)return;
   examplesAiReady={query:query,rows:rows};
   examplesAiNotice('Готово. Нажмите +, чтобы открыть четыре примера.');
  }catch(error){if(run===examplesAiRun)examplesAiNotice('Не удалось подготовить примеры: '+(error&&error.message||error));}
  finally{if(run===examplesAiRun){examplesAiBusy=false;if(ai)ai.removeAttribute('aria-busy');}}
 }
'''
s=s[:start]+new+s[end:]
anchor="  choose(q);\n  var rec=match(q), data=rec&&rec.data||{}, inf=data.infinitive||{};"
replacement="  if(examplesAiBusy){examplesAiNotice('AI ещё создаёт примеры. Дождитесь завершения.');return;}\n  if(examplesAiReady&&examplesAiReady.query===q){choose(q);render(examplesAiReady.rows);displayed=true;return;}\n  examplesAiNotice('Сначала нажмите AI и дождитесь четырёх примеров.');return;\n  var rec=match(q), data=rec&&rec.data||{}, inf=data.infinitive||{};"
assert s.count(anchor)==1,s.count(anchor)
s=s.replace(anchor,replacement,1)
# Clear prepared result on user input. The existing input handler is kept otherwise.
anchor="current=e.target.value.trim();displayed=false;"
assert s.count(anchor)==1
s=s.replace(anchor,"current=e.target.value.trim();examplesAiReady=null;examplesAiRun++;displayed=false;",1)
# Never leave unreachable legacy clipboard code behind: remove old add branch tail.
a=s.index("  var rec=match(q), data=rec&&rec.data||{}, inf=data.infinitive||{};",s.index("if(t.closest('#alwaysAiCodeAdd'))" ,s.index('/* examples-ready-single-request-20261115 */')))
b=s.index("  return;}",a)+len("  return;}")
s=s[:a]+"  return;}"+s[b:]
p.write_text(s,encoding='utf-8')
print('OK: Examples single AI request; + opens prepared examples; no clipboard dialog; other sections unchanged; no backup')
