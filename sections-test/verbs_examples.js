/* Independent examples module. Does not modify the conjugation database. */
(function(){
'use strict';
var KEY='hebrewVerbExamplesRecordsV1';
if(!window.__verbsExamplesSource){var me=document.currentScript;if(me&&me.src){fetch(me.src).then(function(r){return r.text();}).then(function(s){window.__verbsExamplesSource=s;}).catch(function(){});}}
var FILE_DATABASE={
  "לכתוב": {
    "verb": "писать",
    "ru": "писать",
    "uk": "писати",
    "en": "to write",
    "he": "לִכְתּוֹב",
    "aliases": [
      "писать",
      "писати",
      "to write",
      "לִכְתּוֹב"
    ],
    "examples": [
      {
        "he": "אֲנִי כּוֹתֵב מִכְתָּב.",
        "ru": "Я пишу письмо.",
        "uk": "Я пишу листа.",
        "en": "I am writing a letter."
      },
      {
        "he": "הִיא כּוֹתֶבֶת בַּמַּחְבֶּרֶת.",
        "ru": "Она пишет в тетради.",
        "uk": "Вона пише в зошиті.",
        "en": "She writes in the notebook."
      },
      {
        "he": "הוּא כָּתַב סִפּוּר קָצָר.",
        "ru": "Он написал короткий рассказ.",
        "uk": "Він написав коротке оповідання.",
        "en": "He wrote a short story."
      },
      {
        "he": "אֲנִי כָּתַבְתִּי אִימֵייל אֶתְמוֹל.",
        "ru": "Я написал электронное письмо вчера.",
        "uk": "Я написав електронного листа вчора.",
        "en": "I wrote an email yesterday."
      },
      {
        "he": "אֲנַחְנוּ כּוֹתְבִים בְּעִבְרִית.",
        "ru": "Мы пишем на иврите.",
        "uk": "Ми пишемо івритом.",
        "en": "We write in Hebrew."
      },
      {
        "he": "הִיא תִּכְתֹּב לִי מָחָר.",
        "ru": "Она напишет мне завтра.",
        "uk": "Вона напише мені завтра.",
        "en": "She will write to me tomorrow."
      },
      {
        "he": "אַתָּה תִּכְתֹּב אֶת הַתְּשׁוּבָה.",
        "ru": "Ты напишешь ответ.",
        "uk": "Ти напишеш відповідь.",
        "en": "You will write the answer."
      },
      {
        "he": "בְּבַקָּשָׁה, תִּכְתְּבִי אֶת הַשֵּׁם שֶׁלָּךְ.",
        "ru": "Пожалуйста, напиши своё имя.",
        "uk": "Будь ласка, напиши своє ім’я.",
        "en": "Please write your name."
      }
    ]
  },
  "ללמוד": {
    "verb": "учиться",
    "ru": "учиться",
    "uk": "вчитися",
    "en": "to study",
    "he": "לִלְמוֹד",
    "aliases": [
      "учиться",
      "вчитися",
      "to study",
      "לִלְמוֹד"
    ],
    "examples": [
      {
        "he": "אֲנִי לוֹמֵד עִבְרִית בְּכָל יוֹם.",
        "ru": "Я учу иврит каждый день.",
        "uk": "Я вивчаю іврит щодня.",
        "en": "I study Hebrew every day."
      },
      {
        "he": "הִיא לוֹמֶדֶת בָּאוּנִיבֶרְסִיטָה.",
        "ru": "Она учится в университете.",
        "uk": "Вона навчається в університеті.",
        "en": "She studies at the university."
      },
      {
        "he": "אֲנַחְנוּ לוֹמְדִים יַחַד.",
        "ru": "Мы учимся вместе.",
        "uk": "Ми навчаємося разом.",
        "en": "We study together."
      },
      {
        "he": "הוּא לָמַד לַמִּבְחָן אֶתְמוֹל.",
        "ru": "Вчера он готовился к экзамену.",
        "uk": "Учора він готувався до іспиту.",
        "en": "He studied for the exam yesterday."
      },
      {
        "he": "אֲנִי לָמַדְתִּי מִלִּים חֲדָשׁוֹת.",
        "ru": "Я выучил новые слова.",
        "uk": "Я вивчив нові слова.",
        "en": "I learned new words."
      },
      {
        "he": "הֵם יִלְמְדוּ מָחָר בַּבֹּקֶר.",
        "ru": "Они будут учиться завтра утром.",
        "uk": "Вони навчатимуться завтра вранці.",
        "en": "They will study tomorrow morning."
      },
      {
        "he": "אַתְּ תִּלְמְדִי לִקְרוֹא בְּעִבְרִית.",
        "ru": "Ты научишься читать на иврите.",
        "uk": "Ти навчишся читати івритом.",
        "en": "You will learn to read in Hebrew."
      },
      {
        "he": "הַיְלָדִים לוֹמְדִים בְּבֵית הַסֵּפֶר.",
        "ru": "Дети учатся в школе.",
        "uk": "Діти навчаються у школі.",
        "en": "The children study at school."
      }
    ]
  },
  "לקרוא": {
    "verb": "читать",
    "ru": "читать",
    "uk": "читати",
    "en": "to read",
    "he": "לִקְרוֹא",
    "aliases": [
      "читать",
      "читати",
      "to read",
      "לִקְרוֹא"
    ],
    "examples": [
      {
        "he": "אֲנִי קוֹרֵא סֵפֶר מְעַנְיֵן.",
        "ru": "Я читаю интересную книгу.",
        "uk": "Я читаю цікаву книжку.",
        "en": "I am reading an interesting book."
      },
      {
        "he": "הִיא קוֹרֵאת עִתּוֹן בַּבֹּקֶר.",
        "ru": "Она читает газету утром.",
        "uk": "Вона читає газету вранці.",
        "en": "She reads a newspaper in the morning."
      },
      {
        "he": "אֲנַחְנוּ קוֹרְאִים סִפּוּר בְּעִבְרִית.",
        "ru": "Мы читаем рассказ на иврите.",
        "uk": "Ми читаємо оповідання івритом.",
        "en": "We are reading a story in Hebrew."
      },
      {
        "he": "הוּא קָרָא אֶת הַמִּכְתָּב אֶתְמוֹל.",
        "ru": "Он прочитал письмо вчера.",
        "uk": "Він прочитав листа вчора.",
        "en": "He read the letter yesterday."
      },
      {
        "he": "אֲנִי קָרָאתִי אֶת הַהוֹדָעָה.",
        "ru": "Я прочитал сообщение.",
        "uk": "Я прочитав повідомлення.",
        "en": "I read the message."
      },
      {
        "he": "הֵם יִקְרְאוּ אֶת הַסֵּפֶר מָחָר.",
        "ru": "Они прочитают книгу завтра.",
        "uk": "Вони прочитають книжку завтра.",
        "en": "They will read the book tomorrow."
      },
      {
        "he": "אַתְּ תִּקְרְאִי אֶת הַשְּׁאֵלָה.",
        "ru": "Ты прочитаешь вопрос.",
        "uk": "Ти прочитаєш запитання.",
        "en": "You will read the question."
      },
      {
        "he": "בְּבַקָּשָׁה, תִּקְרְאוּ בְּקוֹל רָם.",
        "ru": "Пожалуйста, читайте вслух.",
        "uk": "Будь ласка, читайте вголос.",
        "en": "Please read aloud."
      }
    ]
  }
};
var mode='verbs', current='', menuOpen=false, previousConjugationOpen=false;
function $(id){return document.getElementById(id);}
function lang(){var a=document.querySelector('.reference-controls .lang-btn.active');return a&&a.dataset.lang||document.documentElement.lang||'ru';}
function t(ru,uk,en){return ({ru:ru,uk:uk,en:en})[lang()]||ru;}
function read(){
 var saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){}
 // The JS file is the baseline database; browser changes override its records.
 var combined=Object.assign({},FILE_DATABASE,saved);Object.keys(combined).forEach(function(k){if(combined[k]===null)delete combined[k];});return combined;
}
function downloadJSON(data){
 var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});
 var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='verbs_examples_data.json';document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url);},1500);
}
function exportDatabase(data){
 // A browser cannot overwrite a local JS file. Download its complete replacement.
 try{
  var marker='var FILE_DATABASE=';
  var source=window.__verbsExamplesSource||'';
  if(!source){downloadJSON(data);return;}
  var from=source.indexOf(marker),to=source.indexOf(';',from);
  if(from<0||to<0)return;
  var updated=source.slice(0,from)+marker+JSON.stringify(data,null,2)+source.slice(to);
  var blob=new Blob([updated],{type:'text/javascript;charset=utf-8'});
  var url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='verbs_examples.js';document.body.appendChild(a);a.click();a.remove();
  setTimeout(function(){URL.revokeObjectURL(url);},1500);
 }catch(e){console.warn('Could not export examples file',e);}
}
function write(data){
 try{localStorage.setItem(KEY,JSON.stringify(data));exportDatabase(data);return true;}
 catch(e){alert(t('Не удалось сохранить данные','Не вдалося зберегти дані','Could not save data'));return false;}
}
function norm(v){return String(v||'').normalize('NFKC').toLowerCase().replace(/[\u0591-\u05c7]/g,'').trim();}
function find(q){var db=read(),n=norm(q);return Object.keys(db).find(function(k){var r=db[k];return norm(k)===n||norm(r.verb)===n||[r.ru,r.uk,r.en,r.he].some(function(a){return norm(a)===n;})||((r.aliases||[]).some(function(a){return norm(a)===n;}));});}
function screen(){return $('independentExamplesScreen');}
function render(selectedKey){menuOpen=false;var s=screen();if(!s)return;var db=read(),key=selectedKey&&db[selectedKey]?selectedKey:find(current),r=key&&db[key];s.innerHTML='';if(!current)return;if(!r)return;
var head=document.createElement('div');head.className='independent-word';head.textContent=r.verb;s.appendChild(head);
(r.examples||[]).forEach(function(x){var card=document.createElement('div');card.className='example-card verb';var tr=document.createElement('div');tr.className='example-translation translation';tr.textContent=x[lang()]||'';var he=document.createElement('div');he.className='example-hebrew hebrew';he.dir='rtl';he.textContent=x.he||'';card.appendChild(tr);card.appendChild(he);s.appendChild(card);});}
function wordLabels(record){
 var labels={ru:record.ru||'',uk:record.uk||'',en:record.en||'',he:record.he||''};
 // Existing verb cards provide reliable trilingual infinitive labels.
 var candidates=document.querySelectorAll('#verbsPanel .verbs-list .verb[data-he]');
 for(var i=0;i<candidates.length;i++){
  var d=candidates[i].dataset;
  if(['ru','uk','en','he'].some(function(k){return (norm(record.verb)&&norm(d[k])===norm(record.verb))||(norm(labels[k])&&norm(d[k])===norm(labels[k]));})){
   ['ru','uk','en','he'].forEach(function(k){if(!labels[k])labels[k]=d[k]||'';});break;
  }
 }
 return labels;
}
function list(){
 var s=screen(),db=read(),keys=Object.keys(db).sort(function(a,b){return a.localeCompare(b);});
 s.innerHTML='';menuOpen=true;
 var heading=document.createElement('div');heading.className='independent-list-title';
 heading.textContent=t('В базе данных:','У базі даних:','In the database:');s.appendChild(heading);
 keys.forEach(function(k){
  var record=db[k],labels=wordLabels(record);
  var row=document.createElement('div');row.className='independent-db-row';
  var b=document.createElement('button');b.type='button';b.className='independent-db-open verb';
  var tr=document.createElement('span');tr.className='independent-db-translation translation';
  tr.textContent=labels[lang()]||record.verb||k;
  var he=document.createElement('span');he.className='independent-db-hebrew hebrew';he.dir='rtl';
  he.textContent=labels.he||(/[\u0590-\u05ff]/.test(record.verb||'')?record.verb:'');
  b.appendChild(tr);b.appendChild(he);
  b.onclick=function(e){e.preventDefault();e.stopPropagation();current=record.verb||labels[lang()]||k;$('verbSearch').value=current;render(k);};
  var del=document.createElement('button');del.type='button';del.className='independent-db-del';del.textContent='−';
  del.setAttribute('aria-label',t('Удалить примеры','Видалити приклади','Delete examples'));
  del.onclick=function(){if(!confirm(t('Удалить примеры для этого глагола?','Видалити приклади для цього дієслова?','Delete examples for this verb?')))return;var d=read();d[k]=null;if(write(d))list();};
  row.appendChild(b);row.appendChild(del);s.appendChild(row);
 });
}
function panelClearConjugation(){
 var p=$('verbsPanel');if(!p)return;
 p.classList.remove('table-open','analog-table-open','examples-open');
 // Hide the existing conjugation node itself, regardless of legacy CSS specificity.
 ['conjScreen','examplesScreen'].forEach(function(id){var node=$(id);if(node)node.style.setProperty('display','none','important');});
}

function switchTo(next){
 if(next==='roots'){return;}
 var input=$('verbSearch');
 // A section change never resets the shared selected verb.
 var selected=input?input.value.trim():current;
 menuOpen=false;
 mode=next;
 document.body.classList.toggle('independent-examples-mode',mode==='examples');
 document.querySelectorAll('.reference-section').forEach(function(x,i){
  x.classList.toggle('reference-current',i===(mode==='examples'?1:0));
 });
 current=selected;
 if(input)input.value=selected;
 var ov=$('verbsSavedOverlay');if(ov)ov.classList.remove('open');
 if(mode==='examples'){
  var panel=$('verbsPanel');
  if(panel)previousConjugationOpen=panel.classList.contains('table-open')||panel.classList.contains('analog-table-open');
  panelClearConjugation();
  render();
 } else {
  var s=screen();if(s)s.innerHTML='';
  ['conjScreen','examplesScreen'].forEach(function(id){var node=$(id);if(node)node.style.removeProperty('display');});
  if(previousConjugationOpen&&$('conjScreen')&&$('conjScreen').children.length){$('verbsPanel').classList.add('table-open','analog-table-open');}
 }
}

function prompt(){
 var verb=$('verbSearch').value.trim();
 if(!verb)return;
 // The conjugation section uses a direct ChatGPT link; examples use the same route.
 var msg='Составь ровно 8 естественных примеров употребления глагола иврита «'+verb.replace(/[«»"\\]/g,'')+'» в разных лицах и временах. Все предложения на иврите должны быть с правильными огласовками. Для каждого предложения дай точные переводы на русский, украинский и английский. Ответь ТОЛЬКО готовым JSON-объектом без пояснений и блока markdown. Формат: {"verb":"'+verb.replace(/"/g,'')+'","verb_ru":"инфинитив по-русски","verb_uk":"інфінітив українською","verb_en":"English infinitive","verb_he":"огласованный инфинитив на иврите","examples":[{"he":"предложение на иврите","ru":"русский перевод","uk":"український переклад","en":"English translation"}]}. В examples должно быть ровно 8 полностью заполненных объектов, не шаблоны.';
 var ai=$('alwaysAiCodeAI');
 if(ai){ai.href='https://chatgpt.com/?q='+encodeURIComponent(msg);ai.target='_blank';ai.rel='noopener noreferrer';}
}

function parse(raw){
 var s=raw.trim().replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');var obj;
 try{obj=JSON.parse(s);}catch(e){var a=s.indexOf('{'),b=s.lastIndexOf('}');if(a<0||b<a)throw Error('JSON');obj=JSON.parse(s.slice(a,b+1));}
 if(!obj||!Array.isArray(obj.examples)||!obj.examples.length)throw Error('examples');
 var placeholders=/^(hebrew sentence|russian translation|ukrainian translation|english translation|предложение на иврите|перевод на русский)$/i;
 var examples=obj.examples.map(function(x){
  if(!x||['he','ru','uk','en'].some(function(k){return typeof x[k]!=='string'||!x[k].trim()||placeholders.test(x[k].trim());}))throw Error('placeholder');
  if(!/[\u0590-\u05ff]/.test(x.he))throw Error('hebrew');
  return {he:x.he.trim(),ru:x.ru.trim(),uk:x.uk.trim(),en:x.en.trim()};
 });
 return {verb:String(obj.verb||$('verbSearch').value||'').trim(),examples:examples,verb_ru:String(obj.verb_ru||obj.ru||'').trim(),verb_uk:String(obj.verb_uk||obj.uk||'').trim(),verb_en:String(obj.verb_en||obj.en||'').trim(),verb_he:String(obj.verb_he||obj.he||'').trim()};
}
// JSON is read from the clipboard; no extra modal or form is created.
var pastedExamplesJSON='';
async function add(){
 var requested=$('verbSearch').value.trim(),raw=pastedExamplesJSON;
 try{
  if(navigator.clipboard&&navigator.clipboard.readText){
   var fromClipboard=await navigator.clipboard.readText();
   if(fromClipboard&&fromClipboard.trim())raw=fromClipboard;
  }
 }catch(e){}
 var data;
 try{data=parse(raw);}catch(e){
  // Invalid clipboard text must never be inserted or saved.
  return;
 }
 var db=read(),existing=requested&&find(requested);
 var labels=[data.verb,data.verb_ru,data.verb_uk,data.verb_en,data.verb_he].filter(Boolean);
 var matches=!requested||labels.some(function(x){return norm(x)===norm(requested);});
 if(existing){var oldRecord=db[existing];matches=matches||[oldRecord.verb,oldRecord.ru,oldRecord.uk,oldRecord.en,oldRecord.he].some(function(x){return labels.some(function(y){return norm(x)===norm(y);});});}
 if(!matches){alert(t('Код относится к другому глаголу.','Код належить іншому дієслову.','The code belongs to a different verb.'));return;}
 var key=existing||norm(data.verb_he||data.verb||requested);if(!key)return;
 var old=db[key],merged=(old&&old.examples||[]).slice(),seen=new Set(merged.map(function(x){return norm(x.he);}));
 data.examples.forEach(function(x){if(!seen.has(norm(x.he))){merged.push(x);seen.add(norm(x.he));}});
 var words=wordLabels({verb:data.verb,ru:data.verb_ru,uk:data.verb_uk,en:data.verb_en,he:data.verb_he});
 db[key]={verb:data.verb,examples:merged,aliases:Array.from(new Set([].concat(old&&old.aliases||[],labels,requested).filter(Boolean))),ru:words.ru||(old&&old.ru)||'',uk:words.uk||(old&&old.uk)||'',en:words.en||(old&&old.en)||'',he:words.he||(old&&old.he)||''};
 if(write(db)){current=requested||data.verb;$('verbSearch').value=current;panelClearConjugation();render();}
}
function removeExamples(){
 var key=find($('verbSearch').value.trim()||current);
 if(key){var db=read();db[key]=null;if(!write(db))return;}
 menuOpen=false;render();
}
function intercept(e){
 if(mode!=='examples')return;
 var target=e.target;if(!(target instanceof Element))return;
 var saved=target.closest('.independent-db-open');
 if(saved&&screen()&&screen().contains(saved)){e.preventDefault();e.stopImmediatePropagation();saved.onclick(e);return;}
 var hit=target.closest('#alwaysAiCodeAI,#alwaysAiCodeAdd,#alwaysAiCodeRemove,#sortBtn,#clearVerbSearch');
 if(!hit)return;
 if(hit.id==='alwaysAiCodeAI'){
  prompt();
  // Follow the actual AI anchor, as in conjugations; do not open a second window.
  e.stopImmediatePropagation();
  return;
 }
 e.preventDefault();e.stopImmediatePropagation();
 if(hit.id==='alwaysAiCodeAdd')add();
 else if(hit.id==='alwaysAiCodeRemove')removeExamples();
 else if(hit.id==='sortBtn'){if(menuOpen)render();else list();}
 else if(hit.id==='clearVerbSearch'){current='';menuOpen=false;screen().innerHTML='';$('verbSearch').value='';}
}
function capturePaste(e){
 if(mode!=='examples')return;
 var text=e.clipboardData&&e.clipboardData.getData('text/plain');
 if(!text||text.indexOf('"examples"')<0)return;
 try{parse(text);}catch(_e){return;}
 pastedExamplesJSON=text;
 // Pasting a complete JSON into the shared input imports it without changing the verb.
 if(e.target&&e.target.id==='verbSearch'){e.preventDefault();e.stopImmediatePropagation();add();}
}
function init(){var panel=$('verbsPanel'),wrap=$('verbSearchWrap');if(!panel||!wrap)return;var s=document.createElement('div');s.id='independentExamplesScreen';wrap.insertAdjacentElement('afterend',s);document.querySelectorAll('.reference-section').forEach(function(el,i){if(i>1)return;el.setAttribute('role','button');el.tabIndex=0;el.addEventListener('click',function(){switchTo(i===1?'examples':'verbs');});el.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();switchTo(i===1?'examples':'verbs');}});});$('verbSearch').addEventListener('input',function(){if(mode==='examples'){current=this.value.trim();render();}});document.querySelectorAll('.lang-btn').forEach(function(b){b.addEventListener('click',function(){if(mode==='examples')setTimeout(function(){if(menuOpen)list();else render();},50);});});}
window.addEventListener('click',intercept,true);
window.addEventListener('paste',capturePaste,true);
// Capture input before the legacy conjugation search listeners. They must not
// react to typing in the independent examples section.
window.addEventListener('input',function(e){if(mode==='examples'&&e.target&&e.target.id==='verbSearch'){e.stopImmediatePropagation();current=e.target.value.trim();render();}},true);
window.addEventListener('change',function(e){if(mode==='examples'&&e.target&&e.target.id==='verbSearch')e.stopImmediatePropagation();},true);
window.addEventListener('keydown',function(e){if(mode==='examples'&&e.target&&e.target.id==='verbSearch'&&e.key==='Enter'){e.stopImmediatePropagation();e.preventDefault();e.target.blur();}},true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
