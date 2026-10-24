import json,urllib.request
from pathlib import Path
accounts=json.loads(Path('.qualification/browser-accounts.json').read_text());accounts['customized']=json.loads(Path('.qualification/customized-journey-account.json').read_text())
for mode,a in accounts.items():
 for path in ['/profile','/workout/today']:
  with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8020'+path,headers={'Authorization':'Bearer '+a['token']})) as r:
   assert r.status==200;body=json.load(r)
   if path=='/workout/today':assert body['workout_occurrence_id']==a['session']['workout_occurrence_id'],'Wrong occurrence selected by fixture'
 print(mode,'profile/Today200')
