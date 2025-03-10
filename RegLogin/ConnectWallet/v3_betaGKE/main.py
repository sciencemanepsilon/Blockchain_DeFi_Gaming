import re, threading
from datetime import datetime
from os import environ
from cachetools import TTLCache
#from cachetools import LRUCache
from flask import Flask, request, jsonify, make_response
from myFunc import parseIPs, parseCred, isDocumentExist, SameDeviceFcmLogics
from myFunc import convertOpenDate, checkDevice, callRegLoginApi
from myFunc import queryWallHits, getBaseStats, pfx, writeEmailBonusTx

app = Flask(__name__)
patchMode = environ['PATCH_MODE_LOGIN']
regApi = environ['REGISTER_API']
loginApi = environ['LOGIN_API']
allowed_origins = environ['ALLOWED_ORIGINS'].split("||")
cookName = environ['COOKIE_NAME_string']
web3URL = environ['BLOCKCHAIN_API_LUDO']
web3Route = environ['contractFuncRoute']
addEmailAmount = environ['ADD_EMAIL_AMOUNT']
RegEmailRoute = environ['ADD_EMAIL_ROUTE']

cache = TTLCache(
    maxsize=int(environ['IP_WID_CACHE_SIZE']),
    ttl=int(environ['IP_WID_CACHE_DURATION'])
)
#emailCache = LRUCache(maxsize=int(environ['IP_WID_CACHE_SIZE']))

route = '/prod'
if not pfx: route = '/beta'
cache_lock = threading.Lock()
#email_lock = threading.Lock()
badStrings = frozenset(["", "null", "undefined", None, "object Object"])
print(f"patchMode {patchMode} cookName {cookName}")
print(f"cacheTTL {cache.ttl} size {cache.maxsize} route {route}")


@app.route('/ConnectWallet/hCheck', methods=['GET'])
def healthCheckLB():
    return "OK", 200


@app.route('/AddEmail'+ route, methods=['GET', 'OPTIONS'])
def AddEmail():
    lbOri = request.headers.get('lb-ori')
    referer = request.headers.get('Referer')
    customOri = request.headers.get('Origin')
    print(f"START add email: lbOri {lbOri} referer {referer} cust {customOri}")
    ori = getOri(lbOri, referer, customOri)
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)

    email = request.headers.get('banana')
    tlsLB = request.headers.get('lb-encrypted')
    print(f"TLS {tlsLB} email {email}")

    ipAdd = request.headers.get('lb-ip')
    ipReal = request.access_route[0]
    scook = request.cookies.get(cookName)
    print(f"ip {ipAdd} accRoute {request.access_route}")
    
    reject, ipAdd = valiInput(tlsLB, email, ipAdd, ipReal, scook)
    if reject:
        print(reject)
        return _corsifyRes(jsonify({"error": reject}), ori), 282
    

    err, uid, wid = callREGISTER_toAddGmail(scook, email)
    if err: return _corsifyRes(jsonify({"error":err}), ori), 283
    

    valus = ["game win", "game lose", "bet win", "bet lose", "game draw"]
    if isDocumentExist(f"users/{uid}/Transactions", u"name", u"Reward", u"==", uid):
        return _corsifyRes(jsonify({"error":"already claimed"}), ori), 284
    
    if not isDocumentExist(f"users/{uid}/Transactions", u"name", valus, u"in", uid):
        return _corsifyRes(jsonify({
            "error":"Congratulations! Play one game to get the reward"
        }), ori), 200
    
    
    err, hhash = callWeb3_toPayEmailBonus(wid)
    if err: return _corsifyRes(jsonify(err), ori), 285
    
    writeEmailBonusTx(uid, int(addEmailAmount), hhash)
    print("Email + tx success, End")
    return _corsifyRes(jsonify({"error":"no error", "hash":hhash}), ori), 200



def callWeb3_toPayEmailBonus(wid):
    preRes = callRegLoginApi(
        web3URL + web3Route, {"dummy":"value"},
        {"emailReceiver":wid, "emailAmount":addEmailAmount, "funcName":"SendEmailBonus"}
    )
    print("web3 res: ", preRes.status_code)
    if preRes.status_code > 299 or preRes.status_code < 200:
        return {"error":"web3 failed"},0
    
    res = preRes.json()
    if res['error'] != "no error":
        print(f"{res['error']} details: {res['errorObj']}, End")
        return {"error":res['error'], "errorObj":res['errorObj']},0
    return False, res['hash']


def callREGISTER_toAddGmail(scook, gmailToken):
    preRes = callRegLoginApi(
        regApi + RegEmailRoute,
        {cookName:scook, "banana":gmailToken}, {"dummy":"value"}
    )
    print("Email api res: ", preRes.status_code)
    if preRes.status_code > 299 or preRes.status_code < 200:
        return "email failed",0,0

    res = preRes.json()
    if res['error']:
        print(res['error'], " End")
        return res['error'],0,0
    return False, res['uid'], res['wid']


def valiInput(tlsLB, email, ipAdd, ipReal, scook):
    if scook in badStrings: return "bad request",0
    if email in badStrings: return "missing email",0
    if not tlsLB: return "missing TLS",0
    if tlsLB != "true": return "no TLS forbidden",0
    
    reject, ipAdd = parseIPs(ipAdd, ipReal)
    if reject: return reject, 0

    if ipAdd in cache:
        with cache_lock: cache[ipAdd] = None
        print(f"DDOS-Email-Reward ip {ipAdd}, End")
        return "many calls by this device",0
    #if ipAdd in emailCache: return "Device already exists",0

    with cache_lock: cache[ipAdd] = None
    #with email_lock: emailCache[ipAdd] = None
    #if isDocumentExist(u"users", u"Session.ip", ip, u"==", !!!uid=undefined):
        #return "Device already exists",0
    return False, ipAdd





@app.route('/ConnectWallet'+ route, methods=['GET', 'OPTIONS'])
def connectWallet():
    lbOri = request.headers.get('lb-ori')
    referer = request.headers.get('Referer')
    customOri = request.headers.get('Origin')
    print(f"START: lbOri {lbOri} referer {referer} cust {customOri}")
    ori = getOri(lbOri, referer, customOri)
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)
    
    if patchMode != "0":
        print("patch mode! End")
        return _corsifyRes(jsonify({
            "error":"Our service is currently in maintanence. Please retry later"
        }), ori), 281

    device = request.headers.get('Device')
    isMobile = request.args.get('isMobile')
    wid = request.headers.get('walletid')
    widProvider = request.args.get('widProvider')
    # Register:
    email = None
    nick = request.args.get('nick')
    fmcToken = request.headers.get('fmctoken', default="")
    scook = request.cookies.get(cookName)
    idtoken = request.headers.get('idtoken')
    # Client IP and Location
    ipAdd = request.headers.get('lb-ip')
    ipReal = request.access_route[0]
    countryCode = request.headers.get('lb-country')
    cityLB = request.headers.get('lb-city')
    tlsLB = request.headers.get('lb-encrypted')
    print(f"ip {ipAdd} TLS {tlsLB} device {device}")
    print(f"accRoute {request.access_route} cou {countryCode} ci {cityLB}")

    reject, ipAdd = parseIPs(ipAdd, ipReal)
    if not tlsLB: reject = "missing TLS"
    if tlsLB != "true": reject = "no TLS forbidden"
    if wid in badStrings: reject = "missing wallet id"
    if len(wid) < 12: reject = "invalid wallet id"
    if widProvider in badStrings: reject = "missing wallet provider"
    if device in badStrings: reject = "missing device"
    if not device.replace("_", "").isalnum(): reject = "invalid device"
    if isMobile == "true": isMobile = True
    elif isMobile == "false": isMobile = False
    else: reject = "invalid is mobile"
    if reject:
        print(reject)
        return _corsifyRes(jsonify({"error": reject}), ori), 282

    # START:
    if scook in badStrings:
        print("cookie is null: ", scook)
        scook = None
    else: print("got req.cookie: ", len(scook))
    if idtoken in badStrings:
        print("idtoken is null: ", idtoken)
        idtoken = None
    else: print("got idtoken: ", len(idtoken))
        
    if wid in cache:
        with cache_lock: cache[wid] = None
        print(f"DDOS-Login wid {wid}, End")
        return _corsifyRes(jsonify({"error":"many calls by this wallet"}), ori), 284
    if ipAdd in cache:
            with cache_lock: cache[ipAdd] = None
            print(f"DDOS-Register ip {ipAdd}, End")
            return _corsifyRes(jsonify({"error":"many calls by this IP"}), ori), 283
    
    wall_hits = queryWallHits(u"users", wid)
    res = RegLogin(
        wid, ipAdd, wall_hits, nick, countryCode,
        widProvider, device, fmcToken, email, isMobile, scook, idtoken
    )
    if res['error'] != "no error":
        print(f"{res}, End")
        if res['error'] == "unknown wid with auth.credentials":
            with cache_lock:
                cache[wid] = None
                cache[ipAdd] = None
        return _corsifyRes(jsonify(res), ori), 285
    
    if res['idtoken']:
        with cache_lock:
            cache[wid] = None
            cache[ipAdd] = None
    
    # execute GetDoc Logics
    if wall_hits: uid = wall_hits[0].id
    else:
        uid = res['uid']
        del res['uid']

    tnow = datetime.utcnow().replace(microsecond=0).isoformat() +"Z"
    print("End")
    return _corsifyRes(jsonify({
        **res, "getDoc": {
        "doc": getBaseStats(uid),
        "userDoc": {"countryCode":countryCode, "widProvider":widProvider},
        "inGame":False, "inQue":False, "lastQueDate":tnow, "datetimeNow":tnow
    }}), ori), 200




def getOri(lbOri, referer, customOri):
    if lbOri: return lbOri
    if referer: return referer[:-1]
    if customOri: return customOri
    print("missing ori, End")
    return False

def RegLogin(wid, ipAdd, wall_hits, nick, countryCode,
    widProvider, device, fmcToken, email, isMobile, scook, idtoken):
    if not wall_hits:
        if not nick: return {"error":"nick required when wid NOT exists"}
        if scook or idtoken:
            return {
                "error":"unknown wid with auth.credentials",
                "solution1":"Clear your cookies to use this wallet",
                "solution2":"Pick up the wallet you recently used"
            }
        return exeRegister(
            nick, ipAdd, countryCode, widProvider,
            device, fmcToken, email, isMobile, wid
        )   
    print("wallet exists: ", len(wall_hits))
    if len(wall_hits) > 1:
        print("Critical Error: wid exists twice, End")
        return {"error":"duplicate wallet ids"}
    return exeLogin(wall_hits, device, ipAdd, isMobile, scook, idtoken)


def exeRegister(nick, ipAdd, countryCode, widProvider, device, fmcToken, email, isMobile, wid):
    print(f"Register: got nick {nick} ip {ipAdd} country {countryCode} wallet {widProvider}")
    preRes = callRegLoginApi(
        regApi, {"device":device, "ipAdd":ipAdd, "fmcToken":fmcToken}, {
        "email":email, "isMobile":isMobile,
        "nick":nick, "countryCode":countryCode,
        "wid": wid, "widProvider": widProvider
    })
    print("Regist api res: ", preRes.status_code)
    if preRes.status_code > 299 or preRes.status_code < 200:
        return {"error":"Register failed", "goProfile":False}
    
    regRes = preRes.json()
    if regRes["error"]:
        print("RegApi Error: ", regRes["error"], " End")
        return {"error":regRes["error"], "goProfile":False}

    print("register success, End")
    return {
        "error":"no error", "idtoken":regRes['idtoken'],
        "goProfile":True, "msg":"registration success", "uid":regRes['uid']
    }

def exeLogin(wall_hits, device, ipAdd, isMobile, scookie, idtoken):
    uid = wall_hits[0].id
    userDict = wall_hits[0].to_dict()
    sessDict = userDict['Session']
    print("exeLogin got device: ", device)
    
    if "-" in sessDict['status']:
        print("End, found inGameSess: ", sessDict['status'])
        return {'error':'user in game'}
    if "?" in sessDict['status']:
        print("End, found inQueSess: ", sessDict['status'])
        return {'error':'user in Que'}
    print("not in game/Que, status: ", sessDict['status'])

    if sessDict['status'] != "offline":
        code, msg = checkDevice(sessDict, ipAdd, device, userDict['nickname'])
        if code == 3: return {"error":msg, "idtoken":None, "goProfile":False}
        if code == 1:
            return {
                "error":"no error", "goProfile":True,
                "msg":"user logged in with same device", "idtoken":None
            }
        if scookie in badStrings and idtoken in badStrings: print("noCred, doLogin")
        else:
            newDevice = False
            if msg == "Relogin switching device": newDevice = device
            if scookie == None: scookie = ""
            if idtoken == None: idtoken = ""
            stop = parseCred(uid, newDevice, scookie, idtoken, userDict)
            if stop: return stop
    
    sessCount = -9
    sessDict['openDate'] = convertOpenDate(sessDict['openDate'])
    if "sessCount" in sessDict: sessCount = sessDict['sessCount']

    preRes = callRegLoginApi(
        loginApi, {"dummy":"value"}, {
        "uid":uid, "isMobile":isMobile, "device":device, "ip":ipAdd,
        "sessCount": sessCount, "nick": userDict['nickname']
    })
    print("login api res: ", preRes.status_code)
    if preRes.status_code > 299 or preRes.status_code < 200:
        return {"error":"login failed", "goProfile":False}

    res = preRes.json()
    if res['error']:
        print(res['error'], " End")
        return {"error":res['error'], "goProfile":False}
    
    resData = SameDeviceFcmLogics(ipAdd, device, isMobile, sessCount, res, userDict, uid)
    print(f"{userDict['nickname']} login success, End")
    return resData




def _corsifyRes(x, ori):
    x.headers.add("Access-Control-Allow-Origin", ori)
    x.headers.add("Access-Control-Allow-Credentials", "true")
    return x

def _build_cors_prelight_response(realOri):
    resp = make_response()
    if realOri in allowed_origins:
        resp.headers.add("Access-Control-Allow-Origin", realOri)
    elif re.search(allowed_origins[-1], realOri):
        resp.headers.add("Access-Control-Allow-Origin", realOri)
    else: print("bad origin, End")
    resp.headers.add(
        "Access-Control-Allow-Headers",
        "Device, walletid, fmctoken, idtoken, lb-ip, lb-country, lb-city, lb-encrypted, lb-ori, Referer, Origin, ip, banana"
    )
    resp.headers.add('Access-Control-Allow-Methods', "OPTIONS, GET")
    resp.headers.add("Access-Control-Allow-Credentials", "true")
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)