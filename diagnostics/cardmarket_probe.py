from __future__ import annotations
import argparse, re, sys, urllib.request, urllib.error
from html import unescape

URLS = [
    ("api-product-old","https://api.cardmarket.com/ws/v2.0/output.json/products/1"),
    ("api-product-v2","https://apiv2.cardmarket.com/ws/v2.0/output.json/products/1"),
    ("api-article-old","https://api.cardmarket.com/ws/v2.0/output.json/articles/1"),
    ("api-article-v2","https://apiv2.cardmarket.com/ws/v2.0/output.json/articles/1"),
    ("spoiler-en","https://www.cardmarket.com/en/Pokemon/Spoilers/30th-Celebration"),
    ("singles-en","https://www.cardmarket.com/en/Pokemon/Products/Singles/30th-Celebration"),
    ("gengar-en-frfilter","https://www.cardmarket.com/en/Pokemon/Products/Singles/30th-Celebration/Gengar-ex-V2-30C154?language=2&sortBy=price&sortDir=asc"),
    ("gengar-fr-frfilter","https://www.cardmarket.com/fr/Pokemon/Products/Singles/30th-Celebration/Gengar-ex-V2-30C154?language=2&sortBy=price&sortDir=asc"),
]
BROWSER_HEADERS={
    "User-Agent":"Mozilla/5.0 (Linux; Android 16; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":"fr-FR,fr;q=0.9,en;q=0.7",
    "Cache-Control":"no-cache",
}

def summarize(name, mode, status, final_url, body):
    title=""
    m=re.search(r"<title[^>]*>(.*?)</title>",body,re.I|re.S)
    if m:title=re.sub(r"\s+"," ",unescape(m.group(1))).strip()
    prod_links=len(re.findall(r"/(?:en|fr|de|es|it)/Pokemon/Products/Singles/30th-Celebration/",body,re.I))
    markers={
        "30C154": "30C154" in body or "30C 154" in body,
        "Gengar": "Gengar" in body or "Ectoplasma" in body,
        "French_word": "Français" in body,
        "article-row": "article-row" in body,
        "available_items": "Available items" in body or "Articles disponibles" in body or "Verfügbare Artikel" in body,
    }
    print(f"RESULT name={name} mode={mode} status={status} len={len(body)} prod_links={prod_links} final={final_url}")
    print(f"TITLE {title[:180]}")
    print("MARKERS "+" ".join(f"{k}={int(v)}" for k,v in markers.items()))
    text=re.sub(r"<[^>]+>"," ",body)
    text=re.sub(r"\s+"," ",unescape(text)).strip()
    print("TEXT "+text[:350].replace("\n"," "))

def http_get(name,url,headers):
    req=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(2_000_000); body=raw.decode("utf-8","replace")
            summarize(name,"http-browser" if headers else "http-default",r.status,r.geturl(),body)
    except urllib.error.HTTPError as e:
        raw=e.read(200_000); body=raw.decode("utf-8","replace")
        summarize(name,"http-browser" if headers else "http-default",e.code,e.geturl(),body)
    except Exception as e:
        print(f"RESULT name={name} mode={'http-browser' if headers else 'http-default'} error={type(e).__name__}:{e}")

async def browser_probe():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        ctx=await browser.new_context(locale="fr-FR",user_agent=BROWSER_HEADERS["User-Agent"],viewport={"width":1280,"height":1600})
        page=await ctx.new_page()
        for name,url in URLS:
            try:
                r=await page.goto(url,wait_until="domcontentloaded",timeout=45000)
                await page.wait_for_timeout(1200)
                body=await page.content()
                status=r.status if r else None
                title=await page.title()
                links=await page.locator('a[href*="/Pokemon/Products/Singles/30th-Celebration/"]').count()
                article=await page.locator('.article-row,[data-article-id],[class*="article-row"]').count()
                text=" ".join((await page.locator("body").inner_text()).split())[:500]
                print(f"RESULT name={name} mode=playwright status={status} len={len(body)} links={links} article_rows={article} final={page.url}")
                print(f"TITLE {title[:180]}")
                print(f"TEXT {text}")
            except Exception as e:
                print(f"RESULT name={name} mode=playwright error={type(e).__name__}:{e}")
        await browser.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--browser",action="store_true");args=ap.parse_args()
    for name,url in URLS:
        http_get(name,url,{})
        http_get(name,url,BROWSER_HEADERS)
    if args.browser:
        import asyncio; asyncio.run(browser_probe())

if __name__=="__main__":main()
