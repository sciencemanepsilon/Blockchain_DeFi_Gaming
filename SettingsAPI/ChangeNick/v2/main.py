import uvicorn, httpx
from os import environ
from asyncio import sleep
from typing import Annotated
from nickModule import validateNick
from fastapi import FastAPI, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth, initialize_app, firestore

pfx, esIndex, topicPath, myOris, PubSubCallerApi, custClaimsLabel = (
    environ['DB_COLL_PREFIX'], environ['ES_INDEX_NAME'], environ['CHANGE_NICK_TOPIC_PATH'],
    environ['ALLOWED_ORIGINS'].split("||"), environ['PUBSUB_CALLER_SVC_NAME'], environ['CUSTOM_CLAIMS_ENV_LABEL']
)
corsKwargs = {
    "allow_origins":myOris[0], "allow_methods":["GET", "OPTIONS"],
    "allow_credentials":True, "allow_headers":[
    "Origin", "Referer", "lb-ori", "lb-encrypted", "wid"
]}
route = "/prod"
if not pfx:
    route = "/beta"
    corsKwargs['allow_origins'] = myOris
    corsKwargs['allow_origin_regex'] = myOris[-1]

app = FastAPI()
initialize_app()
db = firestore.client()
hpx = httpx.AsyncClient(timeout=None)
app.add_middleware(CORSMiddleware, **corsKwargs)
print(f"pfx {pfx} ES {esIndex} topic {topicPath} pubsub {PubSubCallerApi} custClaim {custClaimsLabel}")


@app.get('/ChangeNick/HealthCheck')
async def thisHealthCheck():
    return "Health-Check-Success"

@app.get('/PrivateCheckNick/UpdateElastic')
async def privateNick(nick:str):
    await sleep(0)
    print("START: got nick ", nick)
    err  = mainFlow(nick)
    if err: return err
    return {"error":False}



@app.get('/ChangeNick'+ route)
async def nickChange(
    nick:str, wid:Annotated[str, Header()],
    lb_encrypted:Annotated[str, Header()], scookie:Annotated[str, Cookie()]):

    if not scookie:
        print("missing cookie: ", scookie)
        return {"error":"missing cookie"}

    print(f"gott nick {nick}, scookie {len(scookie)} TLS {lb_encrypted}")
    claims, msg = veriCookie(scookie, wid, lb_encrypted)
    print(msg)
    if not claims: return {"error":msg}
    print(f"user {claims['uid']} env {claims['platform']} wid {claims['wid']}")

    err  = mainFlow(nick)
    if err: return err

    res = await hpx.post(
        PubSubCallerApi, json={
        "topicPath":topicPath, "jsonData":None,
        "attributes":{"uid":claims['uid'], "nick":nick, "targetIndex":esIndex}
    })
    print(f"pubsubCaller Res {res.status_code} {res.text}, End")
    if res.status_code != 200: return {"error":"Pubsub elastic call failed"}

    auth.update_user(claims['uid'], display_name=nick)
    db.document(f"{pfx}users/{claims['uid']}").update({u"nickname":nick})
    return {"error":"no error", "success":True}



def mainFlow(nick):
    err = validateNick(nick)
    if err:
        print(err)
        return {"error":err}
    if db.collection(f"{pfx}users").where(u"nickname", u"==", nick).get():
        print("nick already exists, End")
        return {"error":"This name already exists"}
    return False


def veriCookie(cook, wid, lb_encrypted):
    if lb_encrypted != "true": return 0, "no LBE forbidden"
    try: claims = auth.verify_session_cookie(cook, check_revoked=True)
    except Exception as e:
        print(f"sCookie veri failed: {e}")
        return 0, "cookie veri failed"
    if wid != claims['wid']: return 0, "wallet mismatch"
    if custClaimsLabel != claims['platform']: return 0, "env mismatch"
    return claims, "cookie success"

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)