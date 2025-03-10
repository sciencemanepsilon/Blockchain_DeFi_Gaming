import requests
from os import environ
from flask import Flask, request, jsonify, make_response
from firebase_admin import firestore, initialize_app
from myFunc import parseIPs, checkJwtCash
from myFunc import convertOpenDate, checkDevice

walletCash = {}
app = Flask(__name__)
initialize_app()
db = firestore.client()
regApi = environ['REGISTER_API']
loginApi = environ['LOGIN_API']

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
    print(f"ipReal {ipReal} Referer {ori}")

    # Register:
    email = request.headers.get('email')
    nick = request.args.get('nick')
    countryCode = request.args.get('countryCode')
    fmcToken = request.headers.get('fmctoken')

    reject, ipAdd = parseIPs(ipAdd, ipReal)
    if wid in [None, "undefined", ""]: reject = "missing wallet id"
    if len(wid) < 12: reject = "invalid wallet id"
    if widProvider in [None, "", "null", "undefined"]: reject = "missing wallet provider"
    if device in [None, "undefined", ""]: reject = "missing device"
    if isMobile == "true": isMobile = True
    elif isMobile == "false": isMobile = False
    else: reject = "invalid is mobile"
    if email: reject = "email currently not supported"
    #if nick:
        #if not fmcToken: reject = "missing FMC token"
    if reject:
        print(reject)
        return _corsifyRes(jsonify({"error": reject})), 200
    
    # Register new wallet?
    if not nick: print(f"Connect Wallet: got wallet id {wid} ip {ipAdd}")
    else:
        print(f"Register: got nick {nick} ip {ipAdd} country {countryCode} wallet {widProvider}")
        if wid in walletCash:
            if walletCash[wid]:
                print("wallet=True found in walletCash, reject register, End")
                return _corsifyRes(jsonify({"error":"wallet already exists"})), 200
        
        wall_hits = db.collection(f"users").where(u"wid", u"==", wid).get()
        if wall_hits:
            print("wallet exists: ", len(wall_hits), " ,End")
            return _corsifyRes(jsonify({"error":"wallet already exists"})), 200
        
        regRes = requests.post(
            regApi, headers={
                "device":device, "ip":ipAdd, "fmctoken":fmcToken,
                "Authorization":f"Bearer {checkJwtCash('Register', regApi)}"
            }, json={
                "email":email, "isMobile":isMobile,
                "nick":nick, "countryCode":countryCode,
                "wid": wid, "widProvider": widProvider
        }).json()
    
        if regRes["error"]:
            print("RegApi Error: ", regRes["error"], " End")
            return _corsifyRes(jsonify({"error":regRes["error"]})), 200
        
        walletCash[wid] = True
        print("register success, End")
        return _corsifyRes(jsonify({
            "error":"no error", "idtoken":regRes['idtoken'],
            "goProfile":True, "msg":"registration success"
        })), 200

    # LOGIN, wallet belongs to active user?
    wall_hits = db.collection(f"users").where(u"wid", u"==", wid).get()
    if not wall_hits:
        walletCash[wid] = False
        print("cash(wid) set to False, enter nick for Reg, End")
        return _corsifyRes(jsonify({
            "error":"no error", "goProfile":False,
            "msg":"Enter your nick name", "idtoken":None
        })), 200
    
    walletCash[wid] = True
    print("wallet exists: ", len(wall_hits))
    if len(wall_hits) > 1:
        print("Critical Error: wid exists twice, End")
        return _corsifyRes(jsonify({"error": "duplicate wallet ids"})), 200
    
    # wallet id exists, perform login
    uid = wall_hits[0].id
    userDict = wall_hits[0].to_dict()
    sessDict = userDict['Session']

    # in Game?
    if "-" in sessDict['status']:
        print("End, found inGameSess: ", sessDict['status'])
        return _corsifyRes(jsonify({'error':'user in game'})), 200
    if "?" in sessDict['status']:
        print("End, found inQueSess: ", sessDict['status'])
        return _corsifyRes(jsonify({'error':'user in Que'})), 200
    print("not in game/Que, status: ", sessDict['status'])

    # ip and same Device?
    # 1: goProfile noLogin, 2: goProfile + ReLogin, 3: noGo noLogin
    if sessDict['status'] != "offline":
        code, msg = checkDevice(sessDict, ipAdd, device, userDict['nickname'])
        if code == 3:
            return _corsifyRes(jsonify({
                "error":msg, "idtoken":None, "goProfile":False
            })), 200
        if code == 1:
            return _corsifyRes(jsonify({
            "error":"no error", "goProfile":True,
            "msg":"user logged in with same device", "idtoken":None
        })), 200

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
        return _corsifyRes(jsonify({
            "error":"login failed", "goProfile":False
        })), 200

    res = preRes.json()
    if res['error']:
        print(res['error'], " End")
        return _corsifyRes(jsonify({
            "error":res['error'], "goProfile":False
        })), 200

    print(f"{userDict['nickname']} login success, End")
    return _corsifyRes(jsonify({
        "error":"no error", "idtoken":res['idtoken'],
        "goProfile":True, "msg":"login success"
    })), 200


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