import re
from json import loads
from os import environ
from flask import Flask, request, jsonify, make_response
from firebase_admin import firestore, initialize_app, auth
from google.cloud.firestore_v1.base_query import FieldFilter
from myFunc import initRoomLink, genTabConfig
from valid import inputVali, badStrings, checkSess

app = Flask(__name__)
initialize_app()
db = firestore.client()

videoFak, preTc, pfx, patchMode, custClaimLabel, cookName, allowed_origins = (
    environ['VIDEO_BETMIN_FACTOR'], environ['GameConfigArray'],
    environ['DB_COLL_PREFIX'], environ['PATCH_MODE_GAMES'], environ['CUSTOM_CLAIMS_ENV_LABEL'],
    environ['COOKIE_NAME_string'], environ['ALLOWED_ORIGINS'].split("||")
)
tc = genTabConfig(loads(preTc))
route = "beta"
if pfx: route = "prod"
print(f"env: TC {tc} oris {allowed_origins}")

@app.route('/CreateTable/hCheck', methods=['GET'])
def healthCheckLB():
    return "health success", 200

@app.route('/CreateTable/onCreateGameReject/'+ route, methods=['GET', 'OPTIONS'])
def resetSess():
    customOri = request.headers.get('Origin')
    Referer = request.headers.get('Referer')
    lbOri = request.headers.get('lb-ori')
    print(f"ori {customOri} refe {Referer} oriLB {lbOri}")
    ori = getOri(lbOri, Referer, customOri)
    if ori == "error: missing ori":
        print(ori)
        return "error: missing ori", 280
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)

    uid = request.headers.get('uid')
    if uid in badStrings:
        print("missing uid")
        return _corsifyRes(jsonify({"error":"missing params"}), ori), 280

    failed = closeSess(uid, "online")
    if failed: return _corsifyRes(jsonify({"error":failed}), ori), 281
    print(f"Sess reset success for user {uid}, End")
    return _corsifyRes(jsonify({"error":"no error", "success":True}), ori), 200




@app.route('/CreateTable/'+ route, methods=['POST', 'OPTIONS'])
def createTable():
    customOri = request.headers.get('Origin')
    Referer = request.headers.get('Referer')
    lbOri = request.headers.get('lb-ori')
    print(f"START: ori {customOri} referer {Referer} oriLB {lbOri}")
    ori = getOri(lbOri, Referer, customOri)
    if ori == "error: missing ori":
        print(ori)
        return "error: missing ori", 280
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)
    if patchMode != "0":
        print("patch mode! End")
        return _corsifyRes(jsonify({
            "error":"Our service is currently in maintanence. Please retry later"
        }), ori), 280

    scookie = request.cookies.get(cookName)
    device = request.headers.get('device')
    game, betMin, ballance, coinUSD, buyIn, rTimeout, public = (
        request.json.get('game'), request.json.get('betMin'),
        request.json.get('ballance'),request.json.get("MaticUSD"),
        request.json.get('buyIn'), request.json.get('rTimeout'),
        request.json.get('public')
    )
    tid, invPlayers, media, wid = (
        request.json.get('tid'), request.json.get('invPlayers'),
        request.json.get('media'), request.json.get('wid')
    )
    print(f"game {game} tid {tid} wid {wid} public {public}")

    # START
    msg, roomLink, gamePretty, minBetUSD = initRoomLink(
        game, ori, tc, lbOri, Referer
    )
    if not msg:
        print(roomLink)
        return _corsifyRes(jsonify({"error":roomLink}), ori), 281
    
    msg = inputVali(
        ballance, rTimeout, public, device, media, betMin,
        invPlayers, coinUSD, minBetUSD, game, buyIn, videoFak, tid
    )
    if msg:
        print(msg)
        return _corsifyRes(jsonify({"error":msg}), ori), 282

    if scookie in badStrings:
        print(f"bad cookie {scookie}, End")
        return _corsifyRes(jsonify({"error":"missing auth token"}), ori), 282
    try: claims = auth.verify_session_cookie(scookie, check_revoked=True)
    except Exception as e:
        print(f"cook vali failed: {e}")
        return _corsifyRes(jsonify({"error":"cookie expired"}), ori), 283
    if wid != claims['wid']:
        print("wid mismatch, End")
        return _corsifyRes(jsonify({"error":"wallet mismatch"}), ori), 284
    if custClaimLabel != claims['platform']:
        print("env mismatch, End")
        return _corsifyRes(jsonify({"error":"env mismatch"}), ori), 285
    
    currUseruid = claims['uid']
    usDoc = db.document(f"{pfx}users/{currUseruid}").get().to_dict()
    print(f"ballance {ballance} user {currUseruid}")

    err, jsonObj = checkSess(usDoc, device, roomLink)
    print(f"checkSession Res: err {err}, {jsonObj}")
    if err == 1:
        print(jsonObj)
        return _corsifyRes(jsonify(jsonObj), ori), 286
    if err:
        print(jsonObj['error'], " ,End")
        return _corsifyRes(jsonify(jsonObj), ori), 222

    # End
    db.document(f"{pfx}users/{currUseruid}").update({
        u"Session.status": f"lobby-{game}-{tid}"})
    print("End")
    return _corsifyRes(jsonify({
        "error":"no error",
        "link":roomLink + tid + "&gameCollection=" + game
    }), ori), 200



@app.route('/GetFcmReceivers/<uid>', methods=['POST'])
def getFcmReceivers(uid):
    rec = request.get_json()
    print(f"START: admin {uid} receivers {rec}")
    if len(rec) > 0:
        hits = db.collection(
            f"{pfx}users/{uid}/items").where(
            filter=FieldFilter(u"type", u"==", u"friend")).where(
            filter=FieldFilter(u"id",u"not-in",rec)).limit(495-len(rec)).get()
    else:
        hits = db.collection(
            f"{pfx}users/{uid}/items").where(
            filter=FieldFilter(u"type", u"==", u"friend")).limit(495).get()
    for hit in hits: rec.append(hit.to_dict()['id'])
    print(f"len rec {len(rec)}, End")
    return rec, 200



def closeSess(uid, status):
    try: db.document(f"{pfx}users/{uid}").update({u"Session.status":status})
    except Exception as e:
        print(f"db close Sess failed: {e}")
        return "logout failed"
    return False

def getOri(lbOri, Referer, customOri):
    if not lbOri:
        if not Referer:
            if not customOri: return "error: missing ori"
            return customOri
        return Referer[:-1]
    return lbOri


def _corsifyRes(x, ori):
    x.headers.add("Access-Control-Allow-Credentials", "true")
    x.headers.add("Access-Control-Allow-Origin", ori)
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
        "Device, Origin, Referer, lb-ori, uid, Content-Type"
    )
    resp.headers.add('Access-Control-Allow-Methods', "OPTIONS, GET, POST")
    resp.headers.add("Access-Control-Allow-Credentials", "true")
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)