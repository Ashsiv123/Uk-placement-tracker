import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
JOBS=ROOT/'data/jobs.json'
SOURCES=ROOT/'data/sources.json'

def fetch(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 UK-Placement-Tracker/1.0'})
    with urlopen(req,timeout=20) as r:
        return r.read().decode('utf-8','ignore')

data=json.loads(JOBS.read_text())
sources=json.loads(SOURCES.read_text())['sources']
checks=[]
for source in sources:
    try:
        body=fetch(source['url'])
        checks.append({'company':source['company'],'ok':True,'checked':datetime.now(timezone.utc).isoformat(),'fingerprint':hashlib.sha256(body.encode()).hexdigest()[:12]})
    except Exception as exc:
        checks.append({'company':source['company'],'ok':False,'checked':datetime.now(timezone.utc).isoformat(),'error':str(exc)[:160]})
data['updated_at']=datetime.now(timezone.utc).strftime('%d %B %Y %H:%M UTC')
data['source_checks']=checks
JOBS.write_text(json.dumps(data,indent=2))
print(f'Checked {len(checks)} sources')
