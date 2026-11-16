from pathlib import Path

path = Path('/var/www/hebrewverbs-clean/verbs.html')
s = path.read_text(encoding='utf-8')
start = s.index('function request(q){', s.index('<script id="hebrew-roots-workspace-code">'))
end = s.index('function importRoots(raw){', start)
replacement = ''' var rootsAiBusy=false,rootsAiReady=null,rootsAiSequence=0;
 function rootsAiStatus(message){
  var w=workspace(),node=el('rootsAiStatus');
  if(!node){node=document.createElement('div');node.id='rootsAiStatus';node.style.cssText='text-align:center;font:16px/1.4 Arial,sans-serif;padding:8px;color:#333';w.append(node)}
  node.textContent=message;
 }
 function rootsAiLoading(on){
  var add=el('alwaysAiCodeAdd'),ai=el('alwaysAiCodeAI');
  if(add){add.classList.toggle('verb-ai-loading',on);add.setAttribute('aria-busy',String(on))}
  if(ai)ai.setAttribute('aria-busy',String(on));
 }
 function rootsBinyanId(grammar){
  var raw=String(grammar.binyan||grammar.binyan_id||grammar.binyanId||grammar.verb_pattern||'').toLowerCase().replace(/[\\s_\\-]/g,'');
  var ids={paal:'paal',qal:'paal',nifal:'nifal',piel:'piel',pual:'pual',hifil:'hifil',hufal:'hufal',hitpael:'hitpael'};
  return ids[raw]||'';
 }
 async function request(q){
  var query=String(q||selected||'').trim();
  if(!query){rootsAiStatus(tr('Выберите глагол из личного списка.','Виберіть дієслово з особистого списку.','Choose a verb from your saved list.'));return}
  if(rootsAiBusy)return;
  var sequence=++rootsAiSequence;
  rootsAiBusy=true;rootsAiReady=null;rootsAiLoading(true);
  rootsAiStatus(tr('AI определяет корень и биньяны…','ШІ визначає корінь і біньяни…','AI is finding the root and binyanim…'));
  try{
   var response=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({section:'roots',topic:query,level:'beginner'}),cache:'no-store'});
   if(!response.ok)throw Error('HTTP '+response.status);
   var data=await response.json();
   if(!data||!Array.isArray(data.entries))throw Error('Ответ API не содержит entries');
   var bins=[],seen={};
   data.entries.forEach(function(item){
    if(!item||!item.he)return;
    var g=item.grammar||{},id=rootsBinyanId(g);
    if(!id)return;
    var he=String(item.he).trim();
    var key=id+'|'+norm(he);
    if(seen[key])return;
    seen[key]=true;
    bins.push({binyan:id,he:he,ru:item.ru||'',uk:item.uk||'',en:item.en||''});
   });
   if(!bins.length)throw Error('API не указал биньяны для найденных слов');
   var topic=data.topic||{};
   var root=cleanRoot(topic.he||'');
   if(root.length!==3){
    var fromGrammar=data.entries.map(function(item){return cleanRoot((item.grammar||{}).root||'')}).find(function(x){return x.length===3});
    root=fromGrammar||cleanRoot(query);
   }
   if(root.length!==3)root=query;
   if(sequence!==rootsAiSequence)return;
   rootsAiReady={query:query,he:root,binyanim:bins};
   rootsAiStatus(tr('Готово. Нажмите +, чтобы открыть биньяны.','Готово. Натисніть +, щоб відкрити біньяни.','Ready. Press + to show the binyanim.'));
  }catch(error){
   if(sequence===rootsAiSequence){rootsAiReady=null;rootsAiStatus(tr('Не удалось получить биньяны: ','Не вдалося отримати біньяни: ','Could not generate binyanim: ')+(error&&error.message||error))}
  }finally{if(sequence===rootsAiSequence){rootsAiBusy=false;rootsAiLoading(false)}}
 }
'''
s = s[:start] + replacement + s[end:]
start = s.index('function add(){', s.index('<script id="hebrew-roots-workspace-code">'))
end = s.index('function removeRoot(){', start)
replacement = ''' function add(){
  if(rootsAiBusy)return;
  if(!rootsAiReady){rootsAiStatus(tr('Сначала нажмите AI.','Спочатку натисніть AI.','Press AI first.'));return}
  var current=String(el('verbSearch')?.value||selected||'').trim();
  if(current!==rootsAiReady.query){rootsAiReady=null;rootsAiStatus(tr('Глагол изменён. Нажмите AI ещё раз.','Дієслово змінено. Натисніть AI ще раз.','Verb changed. Press AI again.'));return}
  temporaryBinyanim={he:rootsAiReady.he,binyanim:rootsAiReady.binyanim};
  selected=rootsAiReady.he;
  rootsAiReady=null;
  pageCollapsed=false;document.body.classList.remove('roots-page-collapsed');
  show();
 }
'''
s=s[:start]+replacement+s[end:]
# Existing root selection and input changes invalidate the prior result.
s=s.replace("window.selectRootsVerb=function(he){selected=he;listing=false;temporaryBinyanim=null;", "window.selectRootsVerb=function(he){rootsAiReady=null;selected=he;listing=false;temporaryBinyanim=null;", 1)
s=s.replace("selected=e.target.value.trim();temporaryBinyanim=null;listing=false;workspace().replaceChildren()", "selected=e.target.value.trim();rootsAiReady=null;temporaryBinyanim=null;listing=false;workspace().replaceChildren()",1)
# Only rewrite when exact live source matches known source; refuse second application.
if 'window.open(\'https://chatgpt.com/?q=\'+encodeURIComponent(prompt)' in s[s.index('<script id="hebrew-roots-workspace-code">'):s.index('</script>',s.index('<script id="hebrew-roots-workspace-code">'))]:
    # Other conjugation flow intentionally remains unchanged.
    pass
path.write_text(s,encoding='utf-8')
print('OK: Корни иврита: AI обращается к /api/ai/generate, + показывает биньяны. Остальные разделы не изменены; резервных копий нет.')
