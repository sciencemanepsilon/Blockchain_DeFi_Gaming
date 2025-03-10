import uvicorn
from os import environ
from asyncio import sleep
from connections import EsIndexNickWriteSessBQ, getGeo
from firebase import checkNickDB, setAuthObject, writeDB, custTok, addEmailToFire
from fastapi import FastAPI, Request, Header
from typing import Annotated
app = FastAPI()
addEmailRoute = environ['ADD_EMAIL_ROUTE']


@app.post(addEmailRoute)
async def AddEmail(scookie:Annotated[str, Header()], banana:Annotated[str, Header()]):
    await sleep(0)
    print(f"START_EMAIL: got emailToken: {len(banana)}")
    err, uid, wid, email, gNick = addEmailToFire(scookie, banana)
    if err:
        print(err, ", End")
        return {"error":"bad request"}
    if gNick:
        erg = EsIndexNickWriteSessBQ(uid, gNick, None, None, None, None, email, None, "Yes")
    else:
        erg = EsIndexNickWriteSessBQ(uid, "Non", None, None, None, None, email, None, "Non")

    print(f"PubsubCaller Res: {erg.status_code} {erg.text}, End")
    return {"error":False, "wid":wid, "uid":uid}


@app.post('/')
async def register(
    request: Request, ipAdd:Annotated[str, Header()],
    device:Annotated[str, Header()], fmcToken:Annotated[str | None, Header()] = None):

    reqData = await request.json()
    wid, widProvider = reqData['wid'], reqData['widProvider']
    email, isMobile = reqData['email'], reqData['isMobile']
    nick, countryCode = reqData['nick'], reqData['countryCode']
    print(f"got nick {nick} ip {ipAdd} country {countryCode} wid {widProvider}")

    nickRes = checkNickDB(nick)
    if nickRes:
        print(nickRes)
        return {"error":nickRes}
    if not countryCode: countryCode = getGeo(ipAdd)

    # Create Auth Object
    user, errMsg = setAuthObject(nick, countryCode, wid)
    if errMsg: return {"error":errMsg}
    if not user:
        print("user record failed")
        return {"error":"User record creation failed"}

    erg = EsIndexNickWriteSessBQ(
        user.uid, nick, ipAdd,
        isMobile, device, countryCode, email, wid, "NoGmail"
    )
    print(f"PubsubCaller Res: {erg.status_code} {erg.text}")
    
    id_token = custTok(user.uid)
    if len(id_token) < 30:
        print("End")
        return {'error': 'token FB api failed'}

    writeDB(
        email, nick, user.uid, countryCode, fmcToken,
        ipAdd, device, isMobile, wid, widProvider
    )
    print("token success, DB wrote, End")
    return {"error":False, "idtoken":id_token, "uid":user.uid}

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))