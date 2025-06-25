import requests, threading, os, time, re
from flask import Flask, request, jsonify, make_response
from cachetools import TTLCache
from datetime import date, timedelta

app = Flask(__name__)
last_request_time = time.time()
lock = threading.Lock()
sess = requests.Session()
cache = TTLCache(60, 3600)
rateLim = 0.22

route = '/SportRpsLimiter/prod'
routeCache = '/GetCache/prod'
pfx = os.environ['DB_COLL_PREFIX']
allowed_oris = os.environ['ALLOWED_ORIGINS'].split("||")

radidApiKey = os.environ['RAPID_API_KEY']
rapidHost = os.environ['X_RAPID_API_HOST']
minimumTargetURl = os.environ['RAPID_API_MIN_URL_PATH']
if pfx == "":
    route = '/SportRpsLimiter/beta'
    routeCache = '/GetCache/beta'

preUrl = f"https://{rapidHost}/events/search"
cacheUrl = preUrl + "?league_id={}&status=notstarted&date_start={}&date_end={}"

print(f"env, rate {rateLim} rkey {radidApiKey} host {rapidHost}")
print(f"route {route} preUrl {preUrl} allowOri {allowed_oris} cacheUrl {cacheUrl}")

cacheArray = {
    "FIFA World Cup CONMEBOL": 804,
    "FIFA World Cup UEFA": 848,
    "FIFA World Cup Africa": 869,
    "FIFA World Cup Asia": 700,
    "UEFA Champions League": 817,
    "UEFA Europa League": 818,
    "England Premier League": 317,
    "Germany Bundesliga": 512,
    "Spain LaLiga": 251,
    "Italy Serie A": 592,
    "France Ligue 1": 498,
    "Liga Portugal": 203,
    "Turkey SuperLig": 8191,
    "USA MLS": 99,
    "Saudi League": 232,
    "Japan J1": 633,
    "China SuperLeague": 443,
    "Brazil SerieA": 894,
    "Argentine Primera Division": 154,
    "India I-League": 565,
    "NBA": 7422,
    "EuroLeague": 7473,
    "VTB United League": 7377,
    "Argentina de Basquet": 11008,
    "Australia NBL": 7393,
    "Spain Liga ACB": 7378,
    "Turkey Super League": 7403,
    "Novo Basquete Brasil": 7443,
    "Chinese Basketball Association": 7445,
    "National Hockey League": 7588,
    "American Hockey League": 7591,
    "Kontinental Hockey League": 7598,
    "Australian Open": 6878,
    "French Open": 8127,
    "Wimbledon": 6880,
    "US Open": 6881,
    "Nations League": 7749,
    "Nations League Women": 7750,
    "Spain Superliga": 7697,
    "Spain Superliga Women": 7698,
    "Russian League": 7677,
    "Russian League Women": 7678,
    "Portuguese First Division": 7694,
    "Brazil Superliga Women": 7720,
    "World Club Women": 7772,
    "EHF Cup": 7943,
    "EHF Cup Women": 7981,
    "Portugal 1a Divisao": 7872,
    "Spain Asobal": 7884,
    "Russia Super League": 7853,
    "Russia Super League Women": 7854
}


@app.route('/SportRpsLimiter/HealthCheck', methods=['GET'])
def thisHealthCheck():
    return "Health-Check-Success", 200


@app.route(routeCache, methods=['GET', 'OPTIONS'])
def cacheSetter():
    referer = request.headers.get('Referer')
    customOri = request.headers.get('Origin')
    ori = checkOri(None, referer, customOri)
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)

    global last_request_time
    print(f"START cacheSetter: referer {referer} cust {customOri} cacheSize {cache.currsize} len {len(cache)}")

    if len(cache) > 0:
        print("cache exists, keys: ", cache.keys())
        return _corsifyRes(jsonify(dict(cache)), ori), 200

    ii = 0
    dateNow = date.today().isoformat()
    dateEnd = date.today() + timedelta(days=28)
    dateEnd = dateEnd.isoformat()

    for lid in cacheArray.keys():
        with lock:
            elapsed_time = time.time() - last_request_time
            if elapsed_time < rateLim:
                print("mutex is avtice, last req: ", elapsed_time)
                time.sleep(rateLim*1.2)
            last_request_time = time.time()
        
        finalUrl = cacheUrl.format(cacheArray[lid], dateNow, dateEnd)
        print(f"final url {ii} {finalUrl}")
        ii += 1
        try:
            res = sess.post(
                finalUrl,
                headers={"x-rapidapi-key":radidApiKey, "x-rapidapi-host":rapidHost},
                timeout=4
            )
            time.sleep(0.08)
        except Exception as e:
            print(f"rapid api req failed: {e}, set bool false")
            cache[lid] = {'leagueId':cacheArray[lid], 'isGames':False}
            continue
        if res.status_code != 200:
            print(f"error: rapid.res.status {res.status_code}, set bool false")
            cache[lid] = {'leagueId':cacheArray[lid], 'isGames':False}
            continue
        
        jres = res.json()
        if not jres['data']:
            cache[lid] = {'leagueId':cacheArray[lid], 'isGames':False}
        else: cache[lid] = {'leagueId':cacheArray[lid], 'isGames':True}

    print(f"cache built: len {len(cache)} size {cache.currsize} keys {cache.keys()}, End")
    return _corsifyRes(jsonify(dict(cache)), ori), 200




@app.route(route, methods=['GET', 'OPTIONS'])
def limRPS():
    global last_request_time
    url = request.headers.get('targetUrl')
    #lbOri = request.headers.get('lb-ori')
    referer = request.headers.get('Referer')
    customOri = request.headers.get('Origin')
    ori = checkOri(None, referer, customOri)
    print(f"START: referer {referer} cust {customOri} url {url}")
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)
    if not url:
        print("missing url header, End")
        return jsonify({'error': 'missing data'}), 400

    callMethod = sess.get
    if minimumTargetURl not in url:
        print("invalid url header, End")
        return jsonify({'error': 'missing data'}), 400
    elif "/events/search" not in url: ori = "None"
    else: callMethod = sess.post
    with lock:
        elapsed_time = time.time() - last_request_time
        if elapsed_time < rateLim:
            print("mutex is avtice, last req: ", elapsed_time)
            #time.sleep(rateLim - elapsed_time)
            time.sleep(rateLim*1.2)
        last_request_time = time.time()
    try:
        res = callMethod(url, headers={
            "x-rapidapi-key":radidApiKey, "x-rapidapi-host":rapidHost,
        })
    except Exception as e:
        print(f"rapid api req failed: {e}, End")
        return _corsifyRes(jsonify({"error":"target call failed"}), ori), 200
    if res.status_code != 200:
        print(f"error: rapid.res.status {res.status_code}, End")
        return _corsifyRes(jsonify({"error":"rapid api res is not 200"}), ori), 200
    try: jres = res.json()
    except:
        print("json decode failed, End")
        return _corsifyRes(jsonify({"error":"json decode failed"}), ori), 200

    print(f"res keys: {len(jres)}, End")
    return _corsifyRes(jsonify(jres), ori), 200



def checkOri(lbOri, referer, customOri):
    if not lbOri:
        if not referer:
            if not customOri: return "invalid"
            return customOri
        else: return referer[:-1]
    else: return lbOri

def _build_cors_prelight_response(realOri):
    resp = make_response()
    if realOri in allowed_oris:
        resp.headers.add("Access-Control-Allow-Origin", realOri)
    elif pfx == "":
        if re.search(allowed_oris[-1], realOri):
            resp.headers.add("Access-Control-Allow-Origin", realOri)
    else: print("bad origin, End")
    resp.headers.add("Access-Control-Allow-Headers", "lb-ori, Origin, Referer, targetUrl")
    resp.headers.add('Access-Control-Allow-Methods', "OPTIONS, GET")
    return resp


def _corsifyRes(x, ori):
    if ori == "invalid": return x
    x.headers.add("Access-Control-Allow-Origin", ori)
    return x


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)