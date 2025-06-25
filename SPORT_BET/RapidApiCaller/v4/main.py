import uvicorn, httpx, asyncio, os, time
from typing import Annotated
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache
from datetime import date, timedelta

lock = asyncio.Lock()
last_request_time = time.time()

route = '/SportRpsLimiter/prod'
routeCache = '/GetCache/prod'
pfx = os.environ['DB_COLL_PREFIX']
minimumTargetURl = os.environ['RAPID_API_MIN_URL_PATH']
rateLim = float(os.environ['RAPID_API_RPS_LIMIT'])
allowed_oris = os.environ['ALLOWED_ORIGINS'].split("||")
cacheSeconds = int(os.environ['RAPID_API_LEAGUES_CACHE_SECONDS'])

sess = httpx.AsyncClient(timeout=4, headers={
    "x-rapidapi-key":os.environ['RAPID_API_KEY'],
    "x-rapidapi-host":os.environ['X_RAPID_API_HOST']
})
cache = TTLCache(75, cacheSeconds)

corsKwargs = {
    "allow_credentials": False,
    "allow_origins": allowed_oris[0],
    "allow_methods": ["GET", "OPTIONS"],
    "allow_headers": ["lb-ori", "Origin", "Referer", "targetUrl"]
}
if pfx == "":
    route = '/SportRpsLimiter/beta'
    routeCache = '/GetCache/beta'
    corsKwargs['allow_origins'] = allowed_oris
    corsKwargs['allow_origin_regex'] = allowed_oris[-1]

preUrl = f"https://{os.environ['X_RAPID_API_HOST']}/events/search"
cacheUrl = preUrl + "?league_id={}&status=notstarted&date_start={}&date_end={}"

app = FastAPI()
app.add_middleware(CORSMiddleware, **corsKwargs)

print(f"env, rate {rateLim} cacheTTL {cacheSeconds}")
print(f"route {route} preUrl {preUrl} allowOri {allowed_oris} cacheUrl {cacheUrl}")

cacheArray = (
    ("FIFA World Cup CONMEBOL", 804),
    ("FIFA World Cup UEFA", 848),
    ("FIFA World Cup Africa", 869),
    ("FIFA World Cup Asia", 700),
    ("UEFA Champions League", 817),
    ("UEFA Europa League", 818),
    ("England Premier League", 317),
    ("Germany Bundesliga", 512),
    ("Spain LaLiga", 251),
    ("Italy Serie A", 592),
    ("France Ligue 1", 498),
    ("Liga Portugal", 203),
    ("Turkey SuperLig", 8191),
    ("USA MLS", 99),
    ("Saudi League", 232),
    ("Japan J1", 633),
    ("China SuperLeague", 443),
    ("Brazil SerieA", 894),
    ("Argentine Primera Division", 154),
    ("India I-League", 566),
    ("NBA", 7422),
    ("EuroLeague", 7473),
    ("VTB United League", 7377),
    ("Argentina de Basquet", 11008),
    ("Australia NBL", 7393),
    ("Spain Liga ACB", 7378),
    ("Turkey Super League", 7403),
    ("Novo Basquete Brasil", 7443),
    ("Chinese Basketball Association", 7445),
    ("National Hockey League", 7588),
    ("American Hockey League", 7591),
    ("Kontinental Hockey League", 7598),
    ("Australian Open", 6878),
    ("French Open", 8127),
    ("Wimbledon", 6880),
    ("US Open", 6881),
    ("Nations League", 7749),
    ("Nations League Women", 7750),
    ("Spain Superliga", 7697),
    ("Spain Superliga Women", 7698),
    ("Russian League", 7677),
    ("Russian League Women", 7678),
    ("Portuguese First Division", 7694),
    ("Brazil Superliga Women", 7720),
    ("World Club Women", 7772),
    ("EHF Cup", 7943),
    ("EHF Cup Women", 7981),
    ("Portugal 1a Divisao", 7872),
    ("Spain Asobal", 7884),
    ("Russia Super League", 7853),
    ("Russia Super League Women", 7854),
    # new Data
    ("UEFA Conference", 8911),
    ("CONMEBOL Libertadores", 805),
    ("FIBA World Cup", 7475),
    ("FIBA World Cup Q - Europe", 7526),
    ("FIBA World Cup Q - Africa", 7527),
    ("FIBA World Cup Q - Americas", 7528),
    ("FIBA World Cup Q - Asia", 7529),
    ("PBA Philippine Cup", 7416),
    ("IIHF World Championship", 7632),
    ("Sweden SHL", 7604),
    ("Davis Cup", 943),
    ("ATP Cup", 7327),
    ("Fed Cup", 942),
    ("Volleyball World Club Championships", 7771),
    ("Volleyball World Cup", 7747),
    ("Handball European Championship", 7941),
    ("Handball Champions League", 7942),
    ("Handball World Championship", 7940)
)
lenCacheTuple = len(cacheArray)


@app.get('/SportRpsLimiter/HealthCheck')
async def thisHealthCheck():
    return "Health-Check-Success"



@app.get(routeCache)
async def cacheSetter():
    global last_request_time
    print(f"START cacheSetter: cacheSize {cache.currsize} len {len(cache)}")
    if len(cache) > 0:
        print("cache exists, End")
        return dict(cache)

    dateNow = date.today().isoformat()
    dateEnd = date.today() + timedelta(days=28)
    dateEnd = dateEnd.isoformat()
    async with lock:
        elapsed_time = time.time() - last_request_time
        if elapsed_time < rateLim:
            print(f"cache mutex is avtice, last req: {elapsed_time}")
            await asyncio.sleep(rateLim)
        await asyncio.gather(*[
            makeReq(cacheUrl.format(cacheArray[ii][1], dateNow, dateEnd), ii) for ii in range(lenCacheTuple)
        ])
        last_request_time = time.time()
    print(f"cache built: len {len(cache)} size {cache.currsize} keys {cache.keys()}, End")
    return dict(cache)




async def makeReq(finalUrl, off):
    await asyncio.sleep(off * rateLim)
    lid, lnum = cacheArray[off][0], cacheArray[off][1]
    try: res = await sess.post(finalUrl)
    except Exception as e:
        print(f"rapid api req failed: {e}, setting isGames=False")
        cache[lid] = {'leagueId':lnum, 'isGames':False}
        return 0
    
    if res.status_code != 200:
        print(f"error: rapid.res.status {res.status_code}, set bool false")
        cache[lid] = {'leagueId':lnum, 'isGames':False}
        return 0
    
    isGam = True
    if not res.json()['data']: isGam = False
    cache[lid] = {'leagueId':lnum, 'isGames':isGam}
    print(f"league {off} {isGam}")
    return 0




@app.get(route)
async def limRPS(targetUrl:Annotated[str | None, Header()] = None):
    global last_request_time
    print(f"START: url {targetUrl}")
    if not targetUrl:
        print("missing url header, End")
        return JSONResponse(status_code=281, content={"error":281})
    if minimumTargetURl not in targetUrl:
        print("invalid url header, End")
        return JSONResponse(status_code=400, content={"error":"missing data"})
    elif "/events/search" not in targetUrl:
        callMethod = sess.get
        print("events/search not in url, setting httpx.get")
    else: callMethod = sess.post
    async with lock:
        elapsed_time = time.time() - last_request_time
        if elapsed_time < rateLim:
            print("mutex is avtice, last req: ", elapsed_time)
            await asyncio.sleep(rateLim*1.2)
        last_request_time = time.time()
    
    try: res = await callMethod(targetUrl)
    except Exception as e:
        print(f"rapid api req failed: {e}, End")
        return {"error":"target call failed"}
    if res.status_code != 200:
        print(f"error: rapid.res.status {res.status_code}, End")
        return {"error":"rapid api res is not 200"}
    try: jres = res.json()
    except:
        print("json decode failed, End")
        return {"error":"json decode failed"}

    print(f"res keys: {len(jres)}, End")
    return jres


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)