import requests, threading, os, time, re
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
last_request_time = time.time()
lock = threading.Lock()
sess = requests.Session()
rateLim = 0.22
rateLimFake = float(os.environ['RAPID_API_RPS_LIMIT'])
radidApiKey = os.environ['RAPID_API_KEY']

route = '/SportRpsLimiter/prod'
pfx = os.environ['DB_COLL_PREFIX']
patchMode = os.environ['PATCH_MODE_LOGIN']
allowed_oris = os.environ['ALLOWED_ORIGINS'].split("||")
# hosts & targetURLs:
rapidHost = os.environ['X_RAPID_API_HOST']
cricketHost = os.environ['CRICKET_API_HOST']
CricketTargetURL = os.environ['RAPID_API_CRICKET']
minimumTargetURl = os.environ['RAPID_API_MIN_URL_PATH']

if pfx == "": route = '/SportRpsLimiter/beta'
print(f"Server started, rapid maxRPS {rateLim} fake {rateLimFake} {type(rateLimFake)} host {rapidHost}")
print(f"route {route} pfx {pfx} allowOri {allowed_oris}")


@app.route('/SportRpsLimiter/HealthCheck', methods=['GET'])
def thisHealthCheck():
    return "Health-Check-Success", 200


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

    host = rapidHost
    callMethod = sess.get
    if url == CricketTargetURL: host = cricketHost
    elif minimumTargetURl not in url:
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
            "x-rapidapi-key":radidApiKey, "x-rapidapi-host":host,
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