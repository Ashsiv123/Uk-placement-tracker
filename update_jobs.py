import json,re,html
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];JOBS=ROOT/'data/jobs.json';SOURCES=ROOT/'data/sources.json';NOW=datetime.now(timezone.utc)
def fetch_json(url):
 req=Request(url,headers={'User-Agent':'Mozilla/5.0 UK-Placement-Tracker/2.0','Accept':'application/json'})
 with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8','ignore'))
def clean(v):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',str(v or '')))).strip()
def anyterm(t,terms):
 t=t.lower();return any(x.lower() in t for x in terms)
def is_uk(t,terms):return anyterm(t,terms)
def is_placement(t,terms):return anyterm(t,terms) or ('intern' in t.lower() and bool(re.search(r'\b(9|10|11|12|13)\s*[- ]?\s*month',t,re.I)))
def classify(t):
 t=t.lower();f=sum(x in t for x in ['finance','financial','investment','markets','trading','quant','risk','asset management','banking','equities','portfolio']);e=sum(x in t for x in ['engineering','engineer','mechanical','manufacturing','aerospace','systems','hardware','electrical','electronics','energy','product design','mechatronics','fpga']);return 'Engineering + Finance' if f and e else ('Finance' if f else 'Engineering')
def priority(c,title):return min(5,4+(1 if any(x in title.lower() for x in ['industrial placement','placement year','year in industry','mechanical','quant','trading']) else 0))
def deadline(t):
 m=re.search(r'(?:deadline|applications?\s+(?:close|closes|closing))[^A-Za-z0-9]{0,20}(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})',t,re.I)
 if not m:return '',''
 months={m.lower():i for i,m in enumerate(['','January','February','March','April','May','June','July','August','September','October','November','December'])};d,mon,y=m.groups();mo=months.get(mon.lower())
 try:dt=datetime(int(y),mo,int(d),tzinfo=timezone.utc);return f'{int(d)} {mon[:3].title()} {y}',dt.date().isoformat()
 except:return '',''
def greenhouse(s):
 data=fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{s['token']}/jobs?content=true");out=[]
 for j in data.get('jobs',[]):
  title=clean(j.get('title'));loc=clean((j.get('location') or {}).get('name'));body=clean(j.get('content'));out.append({'id':f"greenhouse:{s['token']}:{j.get('id')}",'company':s['company'],'title':title,'location':loc,'url':j.get('absolute_url') or f"https://job-boards.greenhouse.io/{s['token']}/jobs/{j.get('id')}",'text':f'{title} {loc} {body}'})
 return out
def lever(s):
 data=fetch_json(f"https://api.lever.co/v0/postings/{s['site']}?mode=json");out=[]
 for j in data:
  cats=j.get('categories') or {};title=clean(j.get('text'));loc=clean(cats.get('location') or ' '.join(cats.get('allLocations') or []));body=' '.join(clean(j.get(k)) for k in ['descriptionPlain','additionalPlain']);out.append({'id':f"lever:{s['site']}:{j.get('id')}",'company':s['company'],'title':title,'location':loc,'url':j.get('hostedUrl') or f"https://jobs.lever.co/{s['site']}/{j.get('id')}",'text':f'{title} {loc} {body}'})
 return out
cfg=json.loads(SOURCES.read_text());db=json.loads(JOBS.read_text());old={j['id']:j for j in db.get('jobs',[]) if j.get('id')};found={};checks=[]
for s in cfg['sources']:
 if not s.get('enabled',True):continue
 try:
  raws=greenhouse(s) if s['type']=='greenhouse' else lever(s);matched=0
  for r in raws:
   if not is_uk(r['text'],cfg['settings']['uk_terms']) or not is_placement(r['text'],cfg['settings']['placement_terms']):continue
   matched+=1;dl,dli=deadline(r['text']);area=classify(r['text']);m=re.search(r'\b(9|10|11|12|13)\s*[- ]?\s*month',r['text'],re.I);prev=old.get(r['id']);found[r['id']]={'id':r['id'],'company':r['company'],'title':r['title'],'area':area,'status':'Open','priority':priority(r['company'],r['title']),'location':r['location'] or 'UK','duration':f'{m.group(1)} months' if m else 'Placement / internship','deadline':dl,'deadline_iso':dli,'discovered_at':(prev or {}).get('discovered_at') or NOW.isoformat(),'last_seen_at':NOW.isoformat(),'source_type':s['type'],'url':r['url'],'note':"Automatically discovered from the employer's public job feed."}
  checks.append({'company':s['company'],'ok':True,'fetched':len(raws),'matched':matched,'checked':NOW.isoformat()})
 except Exception as e:checks.append({'company':s['company'],'ok':False,'error':str(e)[:180],'checked':NOW.isoformat()})
result=[j for j in old.values() if j.get('source_type')=='manual']+list(found.values());cutoff=NOW-timedelta(days=int(cfg['settings'].get('recently_closed_days',30)))
for jid,p in old.items():
 if p.get('source_type') in ('greenhouse','lever') and jid not in found:
  last=p.get('last_seen_at') or p.get('discovered_at')
  try:ldt=datetime.fromisoformat(last.replace('Z','+00:00')) if last else NOW
  except:ldt=NOW
  if ldt>=cutoff:q=dict(p);q['status']='Closed';q['closed_at']=NOW.isoformat();result.append(q)
result=list({j['id']:j for j in result}.values());result.sort(key=lambda j:(j.get('status')!='Open',-int(j.get('priority',3)),j.get('company','')));JOBS.write_text(json.dumps({'updated_at':NOW.strftime('%d %B %Y %H:%M UTC'),'jobs':result,'source_checks':checks},indent=2,ensure_ascii=False),encoding='utf-8');print(f'Saved {len(result)} jobs; {len(found)} live API placements discovered.')
