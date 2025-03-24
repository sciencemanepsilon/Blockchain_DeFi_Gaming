from os import environ
from json import dumps
from asyncio import gather
from transLib import callContract, db_pfx
from fireLib import validateInput
from flask import Flask, request, jsonify
from BqConnector import userArr, triggerPubsub
app = Flask(__name__)


@app.route('/', methods=['POST'])
async def makeLeaveTable():
    gameColl = request.json.get('gameColl')
    tableId = request.json.get('tableId')
    playerCount = request.json.get('playerCount')
    users = request.json.get('users')
    admin = request.json.get('adminUid')
    mode = request.json.get('mode')
    currency = request.json.get('currency')
    print("START: currency ", currency)
    if not currency: currency = "POL"
    print(f"tab {gameColl}-{tableId} playerCount {playerCount} curr {currency}")

    err, single, players = validateInput(
        tableId, admin, playerCount, users, gameColl, mode
    )
    if err:
        print(err)
        return jsonify({'error':err}), 200
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

    resp = callContract(tableId, plArr, gameColl)
    if resp == 500:
        return jsonify({"error":"Web3.finishHandCall failed", "msg":500, "success":False}), 500
    if resp == 280:
        wTransHistSessPubsub("NotFound", tableId, dat, gameColl, single, players)
        print(f"Leave signle={single} Eventloop closed 280, dat {len(dat)}, End")
        return jsonify({"error":"no error", "success":True, "msg":"Eventloop closed"}), 200
        
    print(f"blockApi Res {resp.status_code}")
    if resp.status_code != 200:
        if resp.status_code in [281, 282]:
            ergJs = resp.json()
            print(ergJs)
            return jsonify(ergJs), 499
        return jsonify({"error":"Web3.finishHand crashed", "msg":resp.status_code, "success":False}), 401
    ergJs = resp.json()
    wTransHistSessPubsub(ergJs['hash'], tableId, dat, gameColl, single, players)
    print(f"Leave signle={single} Success, Len PubSubData {len(dat)}, End")
    return jsonify({"error":"no error", "success":True}), 200


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
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))