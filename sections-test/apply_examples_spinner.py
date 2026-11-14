from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
start=s.find('async function examplesAiGenerate(query)')
end=s.find("window.addEventListener('click'", start)
if start<0 or end<0: raise SystemExit('ERROR: Examples AI handler not found; no changes')
chunk=s[start:end]
old_on="examplesAiProgress('⏳ ИИ создаёт четыре примера...');"
# Match existing text irrespective of emoji variation
import re
matches=re.findall(r"examplesAiProgress\('([^']*)'\);",chunk)
if len(matches)!=2 or matches[1]!='': raise SystemExit(f'ERROR: unexpected progress calls: {matches!r}; no changes')
chunk=chunk.replace("examplesAiProgress('"+matches[0]+"');",'examplesAiSpinner(true);',1)
chunk=chunk.replace("examplesAiProgress('');",'examplesAiSpinner(false);',1)
marker='/* examples-ai-progress-indicator-20261114 */'
if marker not in s: raise SystemExit('ERROR: indicator marker not found; no changes')
if 'function examplesAiSpinner(' in s: raise SystemExit('ERROR: spinner already installed; no changes')
# Function is declared in a later script; function global available by the time user clicks.
fn="""/* examples-ai-spinner-in-plus-20261114 */
function examplesAiSpinner(active){
 var button=document.getElementById('alwaysAiCodeAdd');
 if(!button)return;
 if(active){button.classList.add('verb-ai-loading');button.setAttribute('aria-busy','true');}
 else{button.classList.remove('verb-ai-loading');button.removeAttribute('aria-busy');button.textContent='+';}
}
"""
s=s[:start]+chunk+s[end:]
s=s.replace(marker,fn+marker,1)
p.write_text(s,encoding='utf-8')
print('OK: Examples AI spinner inside +; fixed yellow indicator disabled; conjugation logic unchanged; no backup')
