import requests
from time import time
from datetime import datetime
from os import environ
from flask import Flask, request, jsonify, make_response
from firebase_admin import firestore, initialize_app
from myFunc import parseIPs, checkJwtCash
from myFunc import convertOpenDate, checkDevice

ipCash = {}
walletCash = {}
app = Flask(__name__)
initialize_app()
db = firestore.client()
regApi = environ['REGISTER_API']
loginApi = environ['LOGIN_API']
badStrings = ["", "null", "undefined", None]

@app.route('/', methods=['GET', 'OPTIONS'])
def connectWallet():
    if request.method == "OPTIONS": return _build_cors_prelight_response()
    device = request.headers.get('device')
    isMobile = request.args.get('isMobile')
    ipAdd = request.headers.get('ip')
    ipReal = request.access_route[0]
    ori = request.headers.get('Referer')
    wid = request.headers.get('walletid')
    widProvider = request.args.get('widProvider')
    print(f"ipReal {ipReal} Referer {ori} wid {wid}")
    # Register:
    email = request.headers.get('email')
    nick = request.args.get('nick')
    countryCode = request.args.get('countryCode')
    fmcToken = request.headers.get('fmctoken')

    reject, ipAdd = parseIPs(ipAdd, ipReal)
    if wid in badStrings: reject = "missing wallet id"
    if len(wid) < 12: reject = "invalid wallet id"
    if widProvider in badStrings: reject = "missing wallet provider"
    if device in badStrings: reject = "missing device"
    if isMobile == "true": isMobile = True
    elif isMobile == "false": isMobile = False
    else: reject = "invalid is mobile"
    if email: reject = "email currently not supported"
    #if nick:
        #if not fmcToken: reject = "missing FMC token"
    if reject:
        print(reject)
        return _corsifyRes(jsonify({"error": reject})), 200

    # START:
    if wid not in walletCash:
        if ipAdd in ipCash:
            diff = time() -ipCash[ipAdd]
            if diff < 8:
                ipCash[ipAdd] = time()
                print(f"DDOS-Register ip {ipAdd}, last try {diff} sec, End")
                return _corsifyRes(jsonify({"error":"many calls by this IP"})), 200
        wall_hits = db.collection(f"users").where(u"wid", u"==", wid).get()
        res = Register(
            wid, ipAdd, wall_hits, nick, countryCode,
            widProvider, device, fmcToken, email, isMobile
        )
    else:
        #if nick:
            #print(f"wid inCash, but nick {nick} passed, End")
            #return _corsifyRes(jsonify({"error":"nick forbidden when wid exists"})), 200
        diff = time() -walletCash[wid]
        if diff < 13:
            walletCash[wid] = time()
            print(f"DDOS-Login wid {wid}, last try {diff} sec, End")
            return _corsifyRes(jsonify({"error":"many calls by this wallet"})), 200
        wall_hits = db.collection(f"users").where(u"wid", u"==", wid).get()
        res = Login(
            wid, ipAdd, wall_hits, device, isMobile, nick,
            countryCode, widProvider, fmcToken, email
        )


    if res['error'] != "no error":
        print(f"{res}, End")
        return _corsifyRes(jsonify(res)), 200

    if res['idtoken']:
        walletCash[wid] = time()
        ipCash[ipAdd] = time()
    
    # execute GetDoc Logics
    if wall_hits: uid = wall_hits[0].id
    else:
        uid = res['uid']
        del res['uid']

    tnow = datetime.utcnow().replace(microsecond=0).isoformat() +"Z"
    print("End")
    return _corsifyRes(jsonify({
        **res, "getDoc": {
        "doc": db.document(f"baseStats/{uid}").get().to_dict(),
        "userDoc": {"countryCode":countryCode, "widProvider":widProvider},
        "inGame":False, "inQue":False, "lastQueDate":tnow, "datetimeNow":tnow
    }})), 200
    




def Login(wid, ipAdd, wall_hits, device,
    isMobile, nick, countryCode, widProvider, fmcToken, email):
    print("wallet exists: ", len(wall_hits))
    if len(wall_hits) > 1:
        print("Critical Error: wid exists twice, End")
        return {"error":"duplicate wallet ids"}
    
    if not wall_hits:
        return Register(
            wid, ipAdd, wall_hits, nick, countryCode,
            widProvider, device, fmcToken, email, isMobile
        )
    elif nick: return {"error":"nick forbidden when wid exists"}
    return exeLogin(wall_hits, device, ipAdd, isMobile)

def Register(wid, ipAdd, wall_hits, nick,
    countryCode, widProvider, device, fmcToken, email, isMobile):
    if not wall_hits:
        if not nick: return {"error":"nick required when wid NOT exists"}
        return exeRegister(
            nick, ipAdd, countryCode, widProvider,
            device, fmcToken, email, isMobile, wid
        )   
    return Login(
        wid, ipAdd, wall_hits, device, isMobile,
        nick, countryCode, widProvider, fmcToken, email
    )

def exeRegister(nick, ipAdd, countryCode, widProvider, device, fmcToken, email, isMobile, wid):
    print(f"Register: got nick {nick} ip {ipAdd} country {countryCode} wallet {widProvider}")
    preRes = requests.post(
        regApi, headers={
            "device":device, "ip":ipAdd, "fmctoken":fmcToken,
            "Authorization":f"Bearer {checkJwtCash('Register', regApi)}"
        }, json={
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

def exeLogin(wall_hits, device, ipAdd, isMobile):
    uid = wall_hits[0].id
    userDict = wall_hits[0].to_dict()
    sessDict = userDict['Session']
    # in Game?
    if "-" in sessDict['status']:
        print("End, found inGameSess: ", sessDict['status'])
        return {'error':'user in game'}
    if "?" in sessDict['status']:
        print("End, found inQueSess: ", sessDict['status'])
        return {'error':'user in Que'}
    print("not in game/Que, status: ", sessDict['status'])
    # ip and same Device?
    # 1: goProfile noLogin, 2: goProfile + ReLogin, 3: noGo noLogin
    if sessDict['status'] != "offline":
        code, msg = checkDevice(sessDict, ipAdd, device, userDict['nickname'])
        if code == 3: return {"error":msg, "idtoken":None, "goProfile":False}
        if code == 1:
            return {
                "error":"no error", "goProfile":True,
                "msg":"user logged in with same device", "idtoken":None
            }
    
    sessCount = -9
    sessDict['openDate'] = convertOpenDate(sessDict['openDate'])
    if "sessCount" in sessDict: sessCount = sessDict['sessCount']

    preRes = requests.post(
        loginApi, headers={
            "device":device, "ip":ipAdd,
            "Authorization":f"Bearer {checkJwtCash('Login', loginApi)}"
        }, json={
            "uid":uid, "isMobile":isMobile,
            "sessCount": sessCount, "nick": userDict['nickname']
    })
    print("login api res: ", preRes.status_code)
    if preRes.status_code > 299 or preRes.status_code < 200:
        return {"error":"login failed", "goProfile":False}

    res = preRes.json()
    if res['error']:
        print(res['error'], " End")
        return {"error":res['error'], "goProfile":False}

    print(f"{userDict['nickname']} login success, End")
    return {
        "error":"no error", "idtoken":res['idtoken'],
        "goProfile":True, "msg":"login success"
    }




def _corsifyRes(x): # x = json
    x.headers.add("Access-Control-Allow-Origin", "*")
    return x

def _build_cors_prelight_response():
    resp = make_response()
    resp.headers.add("Access-Control-Allow-Origin", "*")
    resp.headers.add('Access-Control-Allow-Headers', "*")
    resp.headers.add('Access-Control-Allow-Methods', "*")
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))