from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
marker='/* unified-verb-entry-20261115 */'
if marker in s:
 print('OK: already installed');raise SystemExit
anchor=" async function generate(){\n  if(busy)return;\n  var q=txt(el('verbSearch')&&el('verbSearch').value);\n  if(!q){status('Введите глагол');return}"
assert s.count(anchor)==1, 'AI generator anchor missing or ambiguous; no changes'
replacement=""" // unified-verb-entry-20261115: same search and saved-record opening for every input source.
 function savedFor(q){
  var n=norm(q),all;
  if(!n)return null;
  try{all=window.verbsTableCache&&typeof window.verbsTableCache.read==='function'?window.verbsTableCache.read():JSON.parse(localStorage.getItem('hebrewVerbsLocalRecords')||'{}');}catch(e){return null}
  return Object.keys(all||{}).map(function(k){return all[k]}).find(function(rec){
   var d=rec&&rec.data,inf=d&&d.infinitive;
   if(!inf)return false;
   var terms=[rec.base,inf.he,inf.ru,inf.uk,inf.en];
   ['present','past','future','imperative'].forEach(function(t){(Array.isArray(d[t])?d[t]:[]).forEach(function(r){if(r)terms.push(r.he,r.ru,r.uk,r.en)})});
   return terms.some(function(v){return norm(v)===n});
  })||null;
 }
 async function generate(){
  if(busy)return;
  var q=txt(el('verbSearch')&&el('verbSearch').value);
  if(!q){status('Введите глагол');return}
  var saved=savedFor(q);
  if(saved&&typeof window.openSavedVerbRecord==='function'){
   pending=null;
   if(window.openSavedVerbRecord(saved)!==false){status('');return}
  }"""
s=s.replace(anchor,replacement,1)
p.write_text(s,encoding='utf-8')
print('OK: unified input; saved opens immediately; new verb keeps AI -> + -> local database and table; no backup')
