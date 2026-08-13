import json,re,html,hashlib
from datetime import datetime,timezone,timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin
ROOT=Path(__file__).resolve().parent
JOBS=ROOT/"jobs.json";SOURCES=ROOT/"sources.json";NOW=datetime.now(timezone.utc)
def fetch(url,accept="*/*"):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; UKPlacementTracker/3.0)","Accept":accept})
    with urlopen(req,timeout=30) as r:return r.read().decode("utf-8","ignore")
def fetch_json(url):return json.loads(fetch(url,"application/json"))
def clean(s):return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(s or "")))).strip()
def has_any(text,terms):
    t=" "+text.lower()+" ";return any(term.lower() in t for term in terms)
def is_uk(text,terms):return has_any(text,terms)
def is_placement(text,terms):
    t=text.lower();return has_any(t,terms) or bool(re.search(r"\b(9|10|11|12|13)\s*[- ]?\s*months?\b",t) and ("intern" in t or "student" in t))
def classify(text):
    t=text.lower();fin=["finance","financial","investment","asset management","markets","trading","quant","risk","banking","portfolio","equity","credit"];eng=["engineer","engineering","mechanical","manufacturing","aerospace","systems","hardware","electrical","electronics","mechatronics","energy","technical","software"]
    f=sum(x in t for x in fin);e=sum(x in t for x in eng)
    if f and e:return "Engineering + Finance"
    if f:return "Finance"
    return "Engineering"
def priority(company,title):
    p=4 if company.lower() in {"point72","d. e. shaw","blackrock","airbus","leonardo","verkada"} else 3
    if any(k in title.lower() for k in ["industrial placement","industry placement","placement year","mechanical","quant","trading"]):p+=1
    return min(5,p)
def greenhouse(src):
    d=fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{src['board']}/jobs?content=true");out=[]
    for j in d.get("jobs",[]):
        loc=clean((j.get("location") or {}).get("name"));body=clean(j.get("content"));title=clean(j.get("title"))
        out.append({"id":f"greenhouse:{src['board']}:{j.get('id')}","company":src["company"],"title":title,"location":loc,"url":j.get("absolute_url"),"text":f"{title} {loc} {body}","source_type":"greenhouse"})
    return out
def lever(src):
    d=fetch_json(f"https://api.lever.co/v0/postings/{src['site']}?mode=json");out=[]
    for j in d:
        c=j.get("categories") or {};loc=clean(c.get("location") or " ".join(c.get("allLocations") or []));title=clean(j.get("text"));body=clean(j.get("descriptionPlain"))+" "+clean(j.get("additionalPlain"))
        out.append({"id":f"lever:{src['site']}:{j.get('id')}","company":src["company"],"title":title,"location":loc,"url":j.get("hostedUrl"),"text":f"{title} {loc} {body}","source_type":"lever"})
    return out
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.buf=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":self.href=dict(attrs).get("href");self.buf=[]
    def handle_data(self,data):
        if self.href:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href:self.links.append((self.href,clean(" ".join(self.buf))));self.href=None;self.buf=[]
def official_page(src,setg):
    page=fetch(src["url"]);p=Links();p.feed(page);out=[]
    for href,label in p.links:
        if not label or not href or not is_placement(label,setg["placement_terms"]):continue
        url=urljoin(src["url"],href);key=hashlib.sha1(url.encode()).hexdigest()[:14]
        out.append({"id":f"page:{key}","company":src["company"],"title":label,"location":"UK","url":url,"text":label+" UK","source_type":"page"})
    return out
cfg=json.loads(SOURCES.read_text());SET=cfg["settings"];db=json.loads(JOBS.read_text());old={j["id"]:j for j in db.get("jobs",[]) if j.get("id")};seen={};checks=[]
for src in cfg.get("feeds",[]):
    if not src.get("enabled",True):continue
    try:
        rows=greenhouse(src) if src["type"]=="greenhouse" else lever(src);m=0
        for r in rows:
            if not is_uk(r["text"],SET["uk_terms"]) or not is_placement(r["text"],SET["placement_terms"]):continue
            m+=1;prev=old.get(r["id"],{});area=classify(r["text"])
            seen[r["id"]]={"id":r["id"],"company":r["company"],"title":r["title"],"area":area,"status":"Open","priority":priority(r["company"],r["title"]),"location":r["location"] or "UK","duration":"Placement year","deadline":"","deadline_iso":"","discovered_at":prev.get("discovered_at") or NOW.isoformat(),"last_seen_at":NOW.isoformat(),"url":r["url"],"note":"Automatically discovered from the employer's public job feed.","source_type":r["source_type"]}
        checks.append({"company":src["company"],"ok":True,"fetched":len(rows),"matched":m,"checked":NOW.isoformat()})
    except Exception as e:checks.append({"company":src["company"],"ok":False,"error":str(e)[:180],"checked":NOW.isoformat()})
for src in cfg.get("official_pages",[]):
    if not src.get("enabled",True):continue
    try:
        rows=official_page(src,SET);m=0
        for r in rows:
            m+=1;prev=old.get(r["id"],{});area=classify(r["text"])
            seen[r["id"]]={"id":r["id"],"company":r["company"],"title":r["title"],"area":area,"status":"Open","priority":priority(r["company"],r["title"]),"location":"UK","duration":"Placement year","deadline":"","deadline_iso":"","discovered_at":prev.get("discovered_at") or NOW.isoformat(),"last_seen_at":NOW.isoformat(),"url":r["url"],"note":"Automatically discovered on the employer's official careers page.","source_type":"page"}
        checks.append({"company":src["company"],"ok":True,"fetched":"page","matched":m,"checked":NOW.isoformat()})
    except Exception as e:checks.append({"company":src["company"],"ok":False,"error":str(e)[:180],"checked":NOW.isoformat()})
result=[j for j in old.values() if j.get("source_type")=="manual"]+list(seen.values());cutoff=NOW-timedelta(days=30)
for jid,j in old.items():
    if j.get("source_type") not in {"greenhouse","lever","page"} or jid in seen:continue
    when=j.get("last_seen_at") or j.get("discovered_at")
    try:dt=datetime.fromisoformat(when.replace("Z","+00:00")) if when else NOW
    except Exception:dt=NOW
    if dt>=cutoff:
        x=dict(j);x["status"]="Closed";x["closed_at"]=NOW.isoformat();result.append(x)
result=list({j["id"]:j for j in result}.values());result.sort(key=lambda j:(j.get("status")!="Open",-int(j.get("priority",3)),j.get("company",""),j.get("title","")))
JOBS.write_text(json.dumps({"updated_at":NOW.strftime("%d %B %Y %H:%M UTC"),"jobs":result,"source_checks":checks},indent=2,ensure_ascii=False),encoding="utf-8")
print(f"Refresh complete: {len(result)} displayed jobs, {len(seen)} live jobs discovered automatically.")
