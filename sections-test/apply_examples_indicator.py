from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
marker='/* examples-ai-progress-indicator-20261114 */'
if marker in s:
 print('OK: indicator already installed'); raise SystemExit
needle="examplesAiNotice('AI создаёт примеры…');"
if needle not in s:
 raise SystemExit('STOP: expected AI status code not found; no changes')
end="}finally{examplesAiBusy=false;if(ai)ai.removeAttribute('aria-busy');}"
if end not in s:
 raise SystemExit('STOP: expected AI completion code not found; no changes')
# status is independent of the examples screen, which is frequently re-rendered
helper="""/* examples-ai-progress-indicator-20261114 */
function examplesAiProgress(text){
 var id='examples-ai-progress-fixed', node=document.getElementById(id);
 if(!text){if(node)node.remove();return;}
 if(!node){node=document.createElement('div');node.id=id;node.setAttribute('role','status');node.setAttribute('aria-live','polite');
 node.style.cssText='position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:2147483646;background:#fff8d5;border:2px solid #c79800;border-radius:9px;padding:12px 18px;box-shadow:0 3px 15px #0003;color:#111;font:700 16px Arial,sans-serif;text-align:center;max-width:90vw;';document.body.appendChild(node);}
 node.textContent=text;
}
"""
s=s.replace(needle,"examplesAiProgress('⏳ ИИ создаёт четыре примера…');"+needle,1)
s=s.replace(end,"}finally{examplesAiProgress('');examplesAiBusy=false;if(ai)ai.removeAttribute('aria-busy');}",1)
# helper appended after original scripts to avoid altering original code structure
s=s.replace('</body>', '<script>\n'+helper+'</script>\n</body>',1) if '</body>' in s else s+'\n<script>\n'+helper+'</script>\n'
p.write_text(s,encoding='utf-8')
print('OK: AI progress indicator installed in Examples; other sections unchanged; no backup')
