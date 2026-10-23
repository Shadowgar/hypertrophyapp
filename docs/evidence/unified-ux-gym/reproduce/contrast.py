from pathlib import Path
import re,json
css=Path('apps/web/app/appearances.css').read_text()
def lum(hex):
    c=[int(hex[i:i+2],16)/255 for i in (1,3,5)]
    c=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c]
    return .2126*c[0]+.7152*c[1]+.0722*c[2]
def ratio(a,b):
    x,y=sorted([lum(a),lum(b)]);return (y+.05)/(x+.05)
result=[]
for family,mode,body in re.findall(r'html\[data-theme="(.*?)"\]\[data-appearance="(.*?)"\]\s*\{(.*?)\}',css,re.S):
    t=dict(re.findall(r'--([\w-]+):\s*(#[a-fA-F0-9]{6})',body));checks={}
    for text in ('text-primary','text-secondary','text-muted'):
        for bg in ('canvas','surface','surface-raised','surface-selected'):
            checks[text+'/'+bg]=ratio(t[text],t[bg]);assert checks[text+'/'+bg]>=4.5,(family,mode,text,bg,checks[text+'/'+bg])
    for text in ('success-text','warning-text','error-text'):
        checks[text+'/status-surface']=ratio(t[text],t['status-surface']);assert checks[text+'/status-surface']>=4.5
    checks['action-text/action-fill']=ratio(t['action-text'],t['action-fill']);assert checks['action-text/action-fill']>=4.5
    for role in ('border-control','focus'):
        checks[role+'/canvas']=ratio(t[role],t['canvas']);assert checks[role+'/canvas']>=3
    result.append({'family':family,'appearance':mode,'ratios':{k:round(v,2) for k,v in checks.items()}})
assert len(result)==6
Path('docs/evidence/unified-ux-gym/contrast.json').write_text(json.dumps(result,indent=2)+'\n');print('All six token maps: text/status/action >=4.5:1; control border/focus >=3:1 against canvas.')
