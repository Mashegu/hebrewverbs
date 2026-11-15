from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
a=s.find('async function examplesAiGenerate(query){')
b=s.find("window.addEventListener('click',function(e){",a)
if a<0 or b<0: raise SystemExit('STOP: блок примеров не найден')
x=s[a:b]
guard="if(order.some(function(t){return !forms[t].length;})){examplesAiNotice('Для автоматических примеров необходимо полное спряжение выбранного глагола.');return;}"
start='var run=++examplesAiRun;examplesAiBusy=true;'
finish="finally{if(run===examplesAiRun){examplesAiBusy=false;if(ai)ai.removeAttribute('aria-busy');}}"
for item in (guard,start,finish):
 if x.count(item)!=1: raise SystemExit('STOP: ожидаемый код не найден однозначно; изменений нет: '+item[:55])
if 'function examplesAiSpinner(active)' not in s or 'function examplesAiProgress(text)' not in s: raise SystemExit('STOP: индикатор не найден')
x=x.replace(guard,'',1)
x=x.replace(start,start+"examplesAiSpinner(true);examplesAiProgress('ИИ создаёт примеры…');",1)
x=x.replace(finish,"finally{if(run===examplesAiRun){examplesAiBusy=false;if(ai)ai.removeAttribute('aria-busy');examplesAiSpinner(false);examplesAiProgress('');}}",1)
p.write_text(s[:a]+x+s[b:],encoding='utf-8')
print('OK: индикатор AI и ввод глаголов вне списка; остальные разделы не изменены; без резервной копии')
