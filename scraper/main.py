from __future__ import annotations
import asyncio, json, os, re, statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; HIST=DATA/"history"
LATEST=DATA/"latest.json"; STATUS=DATA/"status.json"
BASE="https://www.cardmarket.com"
SET_URL=BASE+"/fr/Pokemon/Products/Singles/30th-Celebration"
SPOILER_URL=BASE+"/fr/Pokemon/Spoilers/30-Anniversaire"
EXPECTED=191; LANG="2"
DELAY=float(os.getenv("REQUEST_DELAY_SECONDS","10"))
TIMEOUT=int(os.getenv("NAV_TIMEOUT_MS","45000"))
MAX_BLOCKS=int(os.getenv("MAX_BLOCKS","3"))
PRICE_RE=re.compile(r"(\d{1,5}(?:[ .\u00a0]\d{3})*(?:[,.]\d{1,2})?)\s*€")
CODE_RE=re.compile(r"\((30C\s+[^)]+)\)",re.I)

def now(): return datetime.now(timezone.utc).replace(microsecond=0)
def iso(d): return d.isoformat().replace("+00:00","Z")
def load(p,default):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return default
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8"); t.replace(p)
def query(url,**kw):
    s=urlsplit(url); q=dict(parse_qsl(s.query)); q.update(kw)
    return urlunsplit((s.scheme,s.netloc,s.path,urlencode(q),s.fragment))
def price(txt):
    m=PRICE_RE.search(txt.replace("\u202f"," "))
    if not m:return None
    x=m.group(1).replace(" ","").replace("\u00a0","")
    if "," in x:x=x.replace(".","").replace(",",".")
    try:return float(x)
    except:return None
def condition(txt):
    low=txt.lower()
    for k,v in [("near mint","NM"),("light played","LP"),("excellent","EX"),("played","PL"),("good","GD"),("poor","PO"),("mint","MT")]:
        if k in low:return v
    m=re.search(r"\b(MT|NM|EX|GD|LP|PL|PO)\b",txt.upper()); return m.group(1) if m else None
def slug(code,url):
    x=(code or url.rstrip("/").split("/")[-1]).lower()
    return re.sub(r"[^a-z0-9]+","-",x).strip("-")
def rarity(code):
    m=re.fullmatch(r"30C\s+(\d{3})",code,re.I)
    if m:
        n=int(m.group(1))
        if 23<=n<=52:return "Pikachu rare"
        if 129<=n<=146:return "Illustration rare"
        if 147<=n<=156:return "Illustration spéciale rare"
        if 157<=n<=158:return "Futuriste rare"
        return "Set principal"
    if "/RGB" in code.upper():return "RGB"
    return "Collection Classique"
def pct(a,b):
    return None if a is None or b in (None,0) else round((a/b-1)*100,2)

async def blocked(page,status):
    if status in (403,429):return True,f"HTTP {status}"
    txt=(await page.locator("body").inner_text()).lower()
    for x in ("captcha","too many requests","access denied","forbidden"):
        if x in txt and len(txt)<20000:return True,x
    return False,None
async def goto(page,url):
    r=await page.goto(url,wait_until="domcontentloaded",timeout=TIMEOUT)
    await page.wait_for_timeout(700); return r.status if r else None

async def discover(page):
    out={}
    for source in [SPOILER_URL]+[query(SET_URL,site=str(i)) for i in range(1,9)]:
        try:
            st=await goto(page,source)
            b,_=await blocked(page,st)
            if b:break
            links=page.locator('a[href*="/fr/Pokemon/Products/Singles/30th-Celebration/"]')
            for i in range(await links.count()):
                a=links.nth(i); href=await a.get_attribute("href"); txt=" ".join((await a.inner_text()).split())
                if not href or not txt:continue
                u=urljoin(BASE,href).split("?")[0]
                cm=CODE_RE.search(txt); code=cm.group(1).strip() if cm else ""
                name=txt[:cm.start()].strip() if cm else txt
                out[u]={"id":slug(code,u),"name":name,"code":code,"url":u,"rarity":rarity(code)}
            if len(out)>=EXPECTED:break
        except PlaywrightTimeoutError:continue
        await asyncio.sleep(max(1,DELAY/2))
    return sorted(out.values(),key=lambda x:x["code"])

async def offers(page):
    q=dict(parse_qsl(urlsplit(page.url).query))
    if q.get("language")!=LANG:return [],None,False,"language-filter-not-confirmed"
    rows=page.locator('.article-row,[data-article-id],[class*="article-row"]')
    arr=[]
    for i in range(await rows.count()):
        row=rows.nth(i); txt=" ".join((await row.inner_text()).split())
        p=None
        for sel in ('.price-container','[class*="article-price"]','[class*="price"]'):
            n=row.locator(sel)
            if await n.count():
                p=price(" ".join((await n.first.inner_text()).split()))
                if p is not None:break
        if p is None:p=price(txt)
        if p is not None:arr.append({"price":round(p,2),"condition":condition(txt)})
    arr.sort(key=lambda x:x["price"])
    body=" ".join((await page.locator("body").inner_text()).split())
    total=None; exact=False
    for pat in [r"(?:sur|de)\s+(\d{1,5})\s+(?:offres?|articles?)",r"(\d{1,5})\s+(?:offres?|articles?)"]:
        m=re.search(pat,body,re.I)
        if m and int(m.group(1))>=len(arr):total=int(m.group(1));exact=True;break
    if total is None:total=len(arr)
    return arr,total,exact,"query-language-2"

def history(days=45):
    cut=now()-timedelta(days=days); out=[]
    for p in sorted(HIST.glob("*.json")) if HIST.exists() else []:
        for s in load(p,{}).get("snapshots",[]):
            try:d=datetime.fromisoformat(s["timestamp"].replace("Z","+00:00"))
            except:continue
            if d>=cut:out.append(s)
    return out
def ref(hist,cid,target,tol):
    best=None
    for s in hist:
        try:d=datetime.fromisoformat(s["timestamp"].replace("Z","+00:00"))
        except:continue
        dist=abs((d-target).total_seconds())
        if dist>tol.total_seconds():continue
        c=next((x for x in s.get("cards",[]) if x.get("id")==cid),None)
        if c and c.get("min_price") is not None and (best is None or dist<best[0]):best=(dist,float(c["min_price"]))
    return best[1] if best else None
def extremes(hist,cid):
    xs=[float(c["min_price"]) for s in hist for c in s.get("cards",[]) if c.get("id")==cid and c.get("min_price") is not None]
    return (min(xs),max(xs)) if xs else (None,None)

async def main():
    DATA.mkdir(exist_ok=True);HIST.mkdir(parents=True,exist_ok=True)
    started=now(); prev=load(LATEST,{"cards":[]}); hist=history(); errors=[]; result=[]; blocks=0
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        ctx=await browser.new_context(locale="fr-FR",viewport={"width":1280,"height":1600})
        page=await ctx.new_page();page.set_default_timeout(TIMEOUT)
        products=await discover(page)
        if not products:
            products=[{k:c.get(k,"") for k in ("id","name","code","url","rarity")} for c in prev.get("cards",[]) if c.get("url")]
        prevmap={c.get("id"):c for c in prev.get("cards",[])}
        for i,prod in enumerate(products):
            if blocks>=MAX_BLOCKS:break
            try:
                st=await goto(page,query(prod["url"],language=LANG,sortBy="price",sortDir="asc"))
                b,why=await blocked(page,st)
                if b:blocks+=1;errors.append({"scope":prod["code"],"message":why});await asyncio.sleep(DELAY);continue
                arr,total,exact,proof=await offers(page)
            except Exception as e:
                errors.append({"scope":prod["code"],"message":type(e).__name__});await asyncio.sleep(DELAY);continue
            if not arr:
                old=prevmap.get(prod["id"])
                if old:
                    old=dict(old);old["fresh"]=False;old["status"]="no_verified_offer";result.append(old)
                errors.append({"scope":prod["code"],"message":"Aucune offre FR vérifiable"});await asyncio.sleep(DELAY);continue
            first=arr[:5]; vals=[x["price"] for x in first]; current=vals[0]; t=now()
            r1=ref(hist,prod["id"],t-timedelta(hours=1),timedelta(hours=2))
            r24=ref(hist,prod["id"],t-timedelta(hours=24),timedelta(hours=3))
            r7=ref(hist,prod["id"],t-timedelta(days=7),timedelta(hours=8))
            r30=ref(hist,prod["id"],t-timedelta(days=30),timedelta(hours=12))
            lo,hi=extremes(hist,prod["id"]); alerts=[]; c24=pct(current,r24); c7=pct(current,r7)
            if c24 is not None and abs(c24)>=10:alerts.append("variation_24h")
            if c7 is not None and abs(c7)>=20:alerts.append("variation_7d")
            if lo is not None and current<lo:alerts.append("nouveau_plus_bas")
            if exact and total<=5:alerts.append("offre_faible")
            result.append({**prod,"min_price":current,"median5":round(float(statistics.median(vals)),2),"lowest_condition":first[0]["condition"],"five_offers":first,"offers_fr":total,"offers_count_exact":exact,"filter_verification":proof,"collected_at":iso(t),"fresh":True,"status":"ok","change_1h":pct(current,r1),"change_24h":c24,"change_7d":c7,"change_30d":pct(current,r30),"historical_low":min(x for x in [lo,current] if x is not None),"historical_high":max(x for x in [hi,current] if x is not None),"alerts":alerts})
            print(f"[{i+1}/{len(products)}] {prod['code']} {current:.2f} EUR",flush=True)
            await asyncio.sleep(DELAY)
        await browser.close()
    ids={c.get("id") for c in result}
    for c in prev.get("cards",[]):
        if c.get("id") not in ids:
            x=dict(c);x["fresh"]=False;x["status"]="stale";result.append(x)
    result.sort(key=lambda x:(x.get("code",""),x.get("name","")))
    fresh=sum(bool(c.get("fresh")) for c in result); status="ok" if fresh==EXPECTED else ("partial" if fresh else "blocked"); done=now()
    latest={"schema":1,"set":"30e Anniversaire / 30C","expected_cards":EXPECTED,"language":"fr","language_id":LANG,"condition_filter":"all","started_at":iso(started),"updated_at":iso(done),"status":status,"discovered_cards":len(products),"fresh_cards":fresh,"errors_count":len(errors),"cards":result}
    save(LATEST,latest)
    compact=[{"id":c["id"],"min_price":c.get("min_price"),"median5":c.get("median5"),"offers_fr":c.get("offers_fr"),"condition":c.get("lowest_condition")} for c in result if c.get("fresh") and c.get("min_price") is not None]
    day=HIST/(done.date().isoformat()+".json"); payload=load(day,{"date":done.date().isoformat(),"snapshots":[]});payload["snapshots"].append({"timestamp":iso(done),"cards":compact});save(day,payload)
    save(STATUS,{"timestamp":iso(done),"status":status,"expected":EXPECTED,"discovered":len(products),"fresh":fresh,"errors":errors[:100],"blocked_events":blocks,"note":"Aucun prix n'est enregistré si le filtre français n'est pas confirmé."})

if __name__=="__main__": asyncio.run(main())
