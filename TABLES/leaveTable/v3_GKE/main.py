import uvicorn
from os import environ
from json import dumps
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from asyncio import gather
from fireLib import validateInput
from transLib import callContract, db_pfx
from BqConnector import userArr, triggerPubsub
app = FastAPI()


@app.post('/')
async def makeLeaveTable(req: Request):
    reqData = await req.json()
    gameColl = reqData.get('gameColl')
    tableId = reqData.get('tableId')
    playerCount = reqData.get('playerCount')
    users = reqData.get('users')
    admin = reqData.get('adminUid')
    mode = reqData.get('mode')
    currency = reqData.get('currency')
    print("START: currency ", currency)
    if not currency: currency = "POL"
    print(f"tab {gameColl}-{tableId} playerCount {playerCount} curr {currency}")

    err, single, players = await validateInput(
        tableId, admin, playerCount, users, gameColl, mode
    )
    if err:
        print(err)
        return {'error':err}
    print(
        f"admin uid {admin} single {single}\n",
        f"len-users {len(users)} 1st user {users[0]['uid']}"
    )
    ress = await gather(*[
        userArr(userEle, gameColl, tableId, currency) for userEle in users
    ])
    dat, plArr = genValues(ress)
    while 0 in plArr: plArr.remove(0)
    print(f"plArrWeb3 {plArr}, plArrPlayedWith {players} PubSub Data {dat}")

    resp = await callContract(tableId, plArr, gameColl)
    if resp == 500:
        return JSONResponse(
            status_code=500, content={
            "error":"Web3.LeaveCall failed", "msg":500, "success":False
        })
    if resp == 280:
        wTransHistSessPubsub("NotFound", tableId, dat, gameColl, single, players)
        print(f"Leave signle={single} Eventloop closed 280, dat {len(dat)}, End")
        return {"error":"no error", "success":True, "msg":"Eventloop closed"}
        
    print(f"blockApi Res {resp.status_code}")
    if resp.status_code != 200:
        if resp.status_code in [281, 282]:
            ergJs = resp.json()
            print(ergJs)
            return JSONResponse(status_code=499, content=ergJs)
        return JSONResponse(
            status_code=401, content={
            "error":"Web3.LeaveTable crashed", "msg":resp.status_code, "success":False
        })
    ergJs = resp.json()
    wTransHistSessPubsub(ergJs['hash'], tableId, dat, gameColl, single, players)
    print(f"Leave signle={single} Success, Len PubSubData {len(dat)}, End")
    return {"error":"no error", "success":True}



def wTransHistSessPubsub(trHash, tableId, dat, gameColl, single, players):
    if single == False: leaveMode = "all"
    else: leaveMode = "single"
    print(f"PubSub caller, single {single} leaveMode {leaveMode}")
    dat['transHash'], dat['playedWith'] = (trHash, players)
    triggerPubsub(
        dumps(dat),
        {"tid":tableId, "gameColl":gameColl, "leaveMode":leaveMode, "db_pfx":db_pfx}
    )
    return 0

def genValues(ress):
    dat, plArr, affiliates = ({},[],[])
    for ele in ress:
        if ele[0]: dat = {**dat, **ele[0]}
        if ele[1]: plArr.append(ele[1])
        if ele[2]: affiliates.append(ele[2])
    return {
        "transHash":None, "statsTransByUid":dat,
        "playedWith":None, "affiliates":affiliates
    }, plArr

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT', 8080)))