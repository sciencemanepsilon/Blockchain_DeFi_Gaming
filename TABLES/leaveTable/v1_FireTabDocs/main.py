from os import environ
from asyncio import gather
from transLib import oriWhiteList, callContract
from fireLib import validateInput, cleanAll
from flask import Flask, request, jsonify, make_response
from BqConnector import userArr, genJsonString, triggerPubsub, genValues
app = Flask(__name__)


@app.route('/unified', methods=['POST', 'OPTIONS'])
async def makeLeaveTable():
    ori = request.headers.get('Referer', default='rejectt')[:-1]
    if request.method == "OPTIONS": return _build_cors_prelight_response(ori)
    gameColl = request.json.get('gameColl')
    tableId = request.json.get('tableId')
    playerCount = request.json.get('playerCount')
    users = request.json.get('users')
    admin = request.json.get('adminUid')
    mode = request.json.get('mode')
    print(f"got {gameColl}-{tableId} from ori {ori}")

    msg, currency, single = validateInput(
        tableId, admin, playerCount, users, gameColl, mode
    )
    if " " in msg:
        print(msg)
        return _corsifyRes(jsonify({'error': msg}), ori), 200
    print(
        f"admin uid {admin} single {single}\n",
        f"len-users {len(users)} 1st user {users[0]['uid']}"
    )
    ress = await gather(*[
        userArr(userEle, gameColl, tableId, currency, single) for userEle in users
    ])
    dat, ERR, plArr = genValues(ress)
    print("plArr: ", plArr)
    tries, nnew = (0, False)
    while tries < 2:
        resp = await callContract(tableId, plArr, tries, nnew)
        if resp != 200:
            tries = tries + 1
            if resp == -9: nnew = True
            else: nnew = False
        else: break
    if resp != 200: print("contract.leaveGame finally failed")

    if len(dat) > 0:
        pubMsg = genJsonString(dat)
        triggerPubsub(pubMsg, {"playedWith":msg, "tid":tableId, "gameColl":gameColl})
    
    if not single: cleanAll(tableId)
    if ERR:
        errVal, succ = ("watch Error Array", False)
        print(f"Error Array {ERR}, Bq Transes {len(dat)}, End")
    else:
        errVal, succ = ("no error", True)
        print(f"leaveAll success, Bq Transes {len(dat)}, End")
    return _corsifyRes(jsonify({"error":errVal, "success":succ, "ErrorArray":ERR}), ori), 200



def _corsifyRes(x, ori):
    x.headers.add("Access-Control-Allow-Origin", ori)
    return x

def _build_cors_prelight_response(ori):
    resp = make_response()
    if ori in oriWhiteList:
        resp.headers.add("Access-Control-Allow-Origin", ori)
    else: print("bad ori: ", ori)
    resp.headers.add('Access-Control-Allow-Headers', "Referer, Content-Type")
    resp.headers.add('Access-Control-Allow-Methods', "POST, OPTIONS")
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))