import uvicorn, asyncio, httpx
from os import environ
from datetime import datetime
from typing import Annotated
from cachetools import TTLCache
from fastapi import FastAPI, Cookie, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore, initialize_app, auth

#"wid", "Origin", "lb-ori", "Referer",
#"lb-ip", "lb-country", "lb-city", "lb-encrypted", "Content-Type"

StatsCash = TTLCache(
    int(environ['STATS_CASH_SIZE']),
    int(environ['STATS_CASH_EXPIRE'])
)
route = "prod"
pfx = environ['DB_COLL_PREFIX']
allowOris = environ['ALLOWED_ORIGINS'].split("||")
custClaimLabel = environ['CUSTOM_CLAIMS_ENV_LABEL']
FCM_SERVER_URL = environ['FCM_SERVER_URL']


corsKwargs = {
    "allow_origins":allowOris[0],
    "allow_methods":["GET", "OPTIONS"],
    "allow_credentials":True, "allow_headers":["*"]
}
if not pfx:
    route = "beta"
    corsKwargs['allow_origins'] = allowOris
    corsKwargs['allow_origin_regex'] = allowOris[-1]

app = FastAPI()
initialize_app()
lock = asyncio.Lock()
db = firestore.client()
hpx = httpx.Client(timeout=None)
app.add_middleware(CORSMiddleware, **corsKwargs)
badStrings = frozenset(["", "null", "undefined", "object Object", None])
print(f"env: pfx {pfx} cors {corsKwargs} clm {custClaimLabel} allowOri {allowOris}")


@app.get('/GetDoc/hCheck')
async def healthCheckLB():
    return "Health-Check-Success"


@app.get('/GetDoc/'+ route +'/FcmProxy/{wid}', status_code=400)
async def ManageFCM(
    wid:str, res:Response,
    fcm: Annotated[str, Header()],
    Origin: Annotated[str, Header()],
    override: Annotated[str, Header()],
    device: Annotated[str | None, Header()] = None,
    lb_ori: Annotated[str | None, Header()] = None,
    scookie: Annotated[str | None, Cookie()] = None,
    lb_encrypted: Annotated[str | None, Header()] = None):

    print(f"START: wid {wid} lbOri {lb_ori} ori {Origin}")
    print(f"crypt {lb_encrypted} override {override}")

    uid = ValidateInput(lb_encrypted, scookie, wid)
    if isinstance(uid, dict): return uid

    if fcm == "remove":
        err, code = callFcmServer(uid, fcm, "dummy", "dummy")
        res.status_code = code
        return {"error":err}
    
    rej = False
    if fcm in badStrings: rej = "invalid fcm"
    if device in badStrings: rej = "null device"
    if not device.replace("_","").isalnum(): rej = "invalid device"
    if override in badStrings: rej = "invalid override"
    if rej:
        print(rej, ", End")
        return {"error":rej}
    
    if override == "false":
        err, code = callFcmServer(uid, fcm, device, override)
        res.status_code = code
        return {"error":err}
    
    if not override.replace("_","").isalnum():
        print("invalid override header, End")
        return {"error":"invalid override"}
    
    err, code = callFcmServer(uid, fcm, device, override)
    res.status_code = code
    return {"error":err}


def callFcmServer(uid, fcm, device, override):
    err = hpx.get(
        FCM_SERVER_URL + f"/Manage/{uid}",
        headers={"fcm":fcm, "device":device, "RemDevice":override}
    )
    print(f"FcmServer: {err.text} {err.status_code}, End")
    if err.status_code == 200: return "no error", err.status_code
    return "FCM server failed", err.status_code





@app.get('/GetDoc/'+ route)
async def makeGetDoc(
    wid:Annotated[str, Header()],
    Origin:Annotated[str, Header()],
    Referer:Annotated[str, Header()],
    lb_ori:Annotated[str | None, Header()] = None,
    lb_ip:Annotated[str | None, Header()] = None,
    lb_country:Annotated[str | None, Header()] = None,
    lb_city:Annotated[str | None, Header()] = None,
    lb_encrypted:Annotated[str | None, Header()] = None,
    scookie:Annotated[str | None, Cookie()] = None):

    print(f"START: wid {wid} lbOri {lb_ori} referer {Referer} ori {Origin}")
    print(f"ip {lb_ip} cou {lb_country} ci {lb_city} cryp {lb_encrypted}")

    uid = ValidateInput(lb_encrypted, scookie, wid)
    if isinstance(uid, dict): return uid

    if uid in StatsCash:
        doc = StatsCash[uid]
        print("statsCash used")
    else:
        doc = fetchDoc("baseStats", uid, pfx)
        async with lock:
            StatsCash[uid] = doc
        print("user not in statsCash, cache set")

    
    docUsers = fetchDoc("users", uid, pfx)
    resUsers = {
        "countryCode": docUsers["countryCode"],
        "widProvider": docUsers["walletProvider"]
    }
    print(f"country {resUsers['countryCode']}")

    inGame = False
    if "-" in docUsers['Session']['status']: inGame = True
    if inGame == True:
        print(f"in game: {inGame}, End")
        return {
            "error":"no error", "success":True, "userDoc":resUsers,
            "doc":doc, "inGame":inGame, "inQue":False, "lastQueDate":None,
            "datetimeNow":datetime.utcnow().isoformat() +"Z"
        }
    
    inQue = checkInQue(uid)
    if inQue == False:
        print(f"in Que: {inQue}, End")
        return {
            "error": "no error", "success": True, "userDoc": resUsers,
            "doc": doc, "inGame": inGame, "inQue": False, "lastQueDate":None,
            "datetimeNow": datetime.utcnow().isoformat() +"Z"
        }

    try: lastQue = docUsers['lastQueDate']
    except: lastQue = datetime.utcnow().replace(microsecond=0).isoformat() +"Z"
    print(f"last Que: {lastQue}, END")
    return {
        "error": "no error", "success": True, "userDoc": resUsers,
        "doc": doc, "inGame": inGame, "inQue": inQue, "lastQueDate": lastQue,
        "datetimeNow": datetime.utcnow().isoformat() +"Z"
    }



def ValidateInput(lb_encrypted, scookie, wid):
    if not lb_encrypted or lb_encrypted == "false":
        print("no TLS, End")
        return {"error":"bad request"}
    if scookie in badStrings:
        print(f"bad cookie {scookie}, End")
        return {"error":"missing auth token"}
    
    try: claims = auth.verify_session_cookie(scookie, check_revoked=True)
    except Exception as e:
        print(f"cook vali failed: {e}")
        return {"error":"cookie veri failed"}
    if wid != claims['wid']:
        print("wid mismatch, End")
        return {"error":"wallet mismatch"}
    if custClaimLabel != claims['platform']:
        print("env mismatch, End")
        return {"error":"env mismatch"}
    return claims['uid']


def fetchDoc(coll, uid, pfx):
    return db.document(f"{pfx}{coll}/{uid}").get().to_dict()

def checkInQue(uid):
    return False

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)