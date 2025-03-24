from os import environ
from json import dumps
from asyncio import gather
from transLib import callContract
from fireLib import validateInput
from flask import Flask, request, jsonify
from BqConnector import userArr, triggerPubsub
app = Flask(__name__)


@app.route('/unified', methods=['POST'])
async def makeLeaveTable():
    ori = request.headers.get('Referer', default='rejectt')[:-1]
    gameColl = request.json.get('gameColl')
    tableId = request.json.get('tableId')
    playerCount = request.json.get('playerCount')
    users = request.json.get('users')
    admin = request.json.get('adminUid')
    mode = request.json.get('mode')
    print(f"got {gameColl}-{tableId} from ori {ori} playerCount {playerCount}")

    err, currency, single = validateInput(
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
        userArr(userEle, gameColl, tableId, currency, single) for userEle in users
    ])
    dat, ERR, plArr = genValues(ress)
    while 0 in plArr: plArr.remove(0)
    print("plArr: ", plArr)

    resp = callContract(tableId, plArr, 0)
    if resp == 500:
        return jsonify({"error":"Web3.finishHandCall failed", "msg":500, "success":False}), 500
    if resp == 280:
        wTransHistSessPubsub("NotFound", tableId, dat, gameColl, single)
        errVal, succ = genErrRes(ERR, dat)
        return jsonify({"error":errVal, "success":succ, "ErrorArray":ERR}), 200
        
    print(f"blockApi Res {resp.status_code}")
    if resp.status_code != 200:
        if resp.status_code in [281, 282]:
            ergJs = resp.json()
            print(ergJs)
            return jsonify(ergJs), 499
        return jsonify({"error":"Web3.finishHand crashed", "msg":resp.status_code, "success":False}), 401
    ergJs = resp.json()
    wTransHistSessPubsub(ergJs['hash'], tableId, dat, gameColl, single)
    errVal, succ = genErrRes(ERR, dat)
    return jsonify({"error":errVal, "success":succ, "ErrorArray":ERR}), 200




def wTransHistSessPubsub(trHash, tableId, dat, gameColl, single):
    leaveMode = "all"
    if single: leaveMode = "single"
    dat['transHash'] = trHash
    triggerPubsub(
        dumps(dat),
        {"tid":tableId, "gameColl":gameColl, "leaveMode":leaveMode, "db_pfx":""})
    return 0

def genErrRes(ERR, dat):
    if ERR:
        errVal, succ = ("watch Error Array", False)
        print(f"Error Array {ERR}, Bq Transes {len(dat)}, End")
    else:
        errVal, succ = ("no error", True)
        print(f"leaveAll success, Bq Transes {len(dat)}, End")
    return errVal, succ

def genValues(ress):
    dat, ERR, plArr = ({},[],[])
    for ele in ress:
        if ele[0]: dat = {**dat, **ele[0]}
        if ele[1]: ERR.append(ele[1])
        if ele[2]: plArr.append(ele[2])
    return {"transHash":None, "statsTransByUid":dat}, ERR, plArr

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))