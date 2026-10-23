import json,hashlib
from pathlib import Path
out=Path('docs/evidence/today-performance-2026-10-23');before=json.loads(Path('.qualification/baseline-payloads.json').read_text());after=json.loads(Path('.qualification/after-payloads.json').read_text())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def differences(a,b,path='$'):
 if type(a)!=type(b):return [path+': type differs']
 if isinstance(a,dict):
  rows=[]
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:rows.append(path+'.'+k+': missing')
   else:rows.extend(differences(a[k],b[k],path+'.'+k))
  return rows
 if isinstance(a,list):
  if len(a)!=len(b):return [path+': length differs']
  return [p for n,(x,y) in enumerate(zip(a,b)) for p in differences(x,y,f'{path}[{n}]')]
 return [] if a==b else [path+': value differs']
results=[]
for key,paths in before.items():
 for path,body in paths.items():
  value=after[key][path];d=differences(body,value);results.append({'scenario':key,'endpoint':'today' if path.endswith('/today') else path.rsplit('/',1)[-1],'exact_equal':not d,'before_sha256':digest(body),'after_sha256':digest(value),'differences':d[:40]})
b=json.loads((out/'baseline-database.json').read_text());a=json.loads((out/'after-database.json').read_text());tables={key:b['tables'][key]==a['tables'][key] for key in b['tables']}
report={'endpoint_count':len(results),'all_endpoint_payloads_exactly_equal':all(r['exact_equal'] for r in results),'payloads':results,'scope':b['scope'],'all_scoped_training_tables_equal':all(tables.values()),'training_tables':tables}
(out/'preservation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['payloads','scope']}))
