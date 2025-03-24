import os, requests
from time import time
from Tasks import checkSess
from flask import Flask, request, jsonify
from firebase_admin import firestore, initialize_app, auth
from myFunc import notiContents, initRoomLink, decideMassPush
from myFunc import traffInfo, updateTrafficInfo, genTableDict
from valid import inputVali, botUserRecord, getJWT
app = Flask(__name__)

res = requests.get(
    os.environ['SYS_CONFIG_API'], params={"oriApi":"CreateTable"},
    headers={"Authorization":f"Bearer {getJWT(os.environ['SYS_CONFIG_API'])}"}
).json()

initialize_app()
db = firestore.client()
Bearer = {"jwt":None, "age":None}
beta, liveDom, massPushApi, coinNamesDict, videoFak, bo = (
    res['api_urls']['beta'], res['api_urls']['live'],
    res['api_urls']['massPushApi'],
    res['coinNamesDict'], res['videoFak'], res['BotRecord']
)
tc, blockApi, taskCaller = (
    res['tableConfig'],
    res['api_urls']['blockchainApi'],
    res['api_urls']['taskCallerApi']
)
bot = botUserRecord(bo['uid'], bo['nick'], bo['photo'], getJWT(blockApi))


@app.route('/openTable', methods=['POST'])
def createTable():
    ori = request.headers.get('ori')
    uid = request.headers.get('uid')
    device = request.headers.get('device')
    
    game, betMin, ballance, coinName, buyIn, rTimeout, public, allowWat = (
        request.json.get('game'), request.json.get('betMin'),
        request.json.get('ballance'), request.json.get('coinName'),
        request.json.get('buyIn'), request.json.get('rTimeout'),
        request.json.get('public'), request.json.get('allowWat')
    )
    tid, adminStart, invPlayers, media, fromQue, gameTime = (
        request.json.get('tid'),
        request.json.get('adminStart'),
        request.json.get('invPlayers'), request.json.get('media'),
        request.json.get('fromQue'), request.json.get('gameTime')
    )
    if coinName not in coinNamesDict:
        print("invalid coinName")
        return "invalid currency type", 281
    if not fromQue: fromQue = False
    coinUSD = request.json.get(coinNamesDict[coinName])
    print(f"uid {uid} game {game} tid {tid} fromQ {fromQue}")

    # START
    msg, roomLink, minBetUSD, seats, gamePretty = initRoomLink(
        game, beta, liveDom, ori, tc
    )
    if not msg:
        print(roomLink); return roomLink, 282
    
    msg = inputVali(
        allowWat, adminStart, ballance, rTimeout,
        public, device, media, betMin, invPlayers,
        fromQue, coinUSD, minBetUSD, game, buyIn, videoFak
    )
    if msg:
        print(msg); return msg, 283

    if not fromQue:
        if tid: currUser = auth.get_user(uid)
        else: currUser = botUserRecord(uid, None, None, None)
    else: currUser = auth.get_user(uid)
    print(f"ballance {ballance} {coinName}")

    if not fromQue and not tid:
        # Check Sess
        usDoc = db.document(f"users/{currUser.uid}").get().to_dict()
        err, jsonObj = checkSess(usDoc, device, roomLink)
        if err == 1:
            print(jsonObj); return jsonObj, 284
        if err:
            print(jsonObj['error'], " ,End")
            return jsonify(jsonObj), 222
        
        # call Smart Contract Function
        ref = db.collection(u"tables").document()
        resp = callContract(betMin, ref.id, game, bot.token)
        print(f"blockApi Res {resp.text} {resp.status_code}")
        if resp.status_code != 200:
            bot.token = getJWT(blockApi)
            resp = callContract(betMin, ref.id, game, bot.token)
            print(f"blockApi Res {resp.text} {resp.status_code}")
            if resp.status_code != 200:
                return "thirdWeb.createGame failed", 285
        
        print(f"genTid {ref.id} + crrateGame Success, End")
        return jsonify({"error":"no error", "tableId":ref.id}), 200

    # ELSE: fromQue OR tid == True
    updateTrafficInfo()
    if game != "pokerTournament_Tables": buyIn = 0.0
    if len(invPlayers) > 0:
        notiText = "You invited "
        if fromQue: notiText = "We notified "
        notiText = createNoti(notiText, invPlayers)
    else: notiText = ""
    ww = notiContents(
        currUser.display_name, gamePretty,
        notiText, buyIn, fromQue, coinName
    )
    tabLobby = genTableDict(
        media, currUser.uid, betMin, buyIn, rTimeout, allowWat,
        public, adminStart, seats, firestore.SERVER_TIMESTAMP,
        game, coinName, invPlayers
    )
    if not gameTime or not isinstance(gameTime, int): gameTime = 0
    if gameTime > 0: tabLobby['table']['gameTime'] = gameTime
    
    if fromQue:
        ref = db.collection(u"tables").document()
        meineId = ref.id
        ref.set(tabLobby)
    if tid:
        meineId = tid
        db.collection(u"tables").document(tid).set(tabLobby)
    
    print(f"opened new table {meineId}, fromQue: {fromQue}")
    db.document(f"users/{currUser.uid}").update({
        u"Session.status": f"lobby-{game}-{meineId}"})
    
    # decision about massPush = randFak
    """if public == False or ori == beta : randFak = 0
    else:
        randFak = decideMassPush(
            traffInfo['req/h'],
            tc['pushNoti']['nUsers'],
            tc['pushNoti']['pushAllUserLimit'],
            tc['pushNoti']['pushAllReqHourLimit'],
            tc['pushNoti']['pushRandomReqHourLimit']
        )"""
    invStr, randFak = "", 0
    payload = {
        "psub": {
            "invStr": invStr,
            "meineId":meineId, "gameAtt1":game, "currUser":currUser.uid,
            "wlink":"", "wmsg":ww['msg'], "wmsg2":ww['msg2'], "botUid":bot.uid,
            "botNick":bot.display_name, "botPhoto":bot.photo_url, "game":gamePretty,
            "dateSched": "no", "diff": "1600.0", "roomLink": roomLink
        },
        "mPush": {
            "wmsg":ww['massPush'], "randFak":randFak, "invP":invPlayers,
            "currUser": currUser.uid, "nUsers": 0,
            "link": roomLink + meineId + "&gameCollection=" + game
        }
    }
    """if not Bearer['jwt']:
        Bearer['jwt'] = getJWT(taskCaller)
        Bearer['age'] = time()
    else:
        diff = time() -Bearer['age']
        if diff > 53 *60:
            Bearer['jwt'] = getJWT(taskCaller)
            Bearer['age'] = time()
    
    res = requests.post(
        taskCaller +"/createTableDownStreamTasks", json=payload,
        headers={"Authorization":f"Bearer {Bearer['jwt']}"}
    )
    print(f"TaskCaller {res.status_code} {res.text}, End")"""
    print("End")
    return jsonify({
        "error":"no error",
        "link":roomLink + meineId + "&gameCollection=" + game
    }), 200


def callContract(betMin, tid, col, token):
    return requests.post(
        blockApi +"/ContractFunc",
        json={"funcName":"createGame",
        "betMin":betMin, "tid":tid, "col":col},
        headers={"Authorization":f"Bearer {token}"}
    )

def createNoti(text, invPlayers):
    firePl = []
    for pl in invPlayers:
        firePl.append(auth.UidIdentifier(pl))
    
    usersResult = auth.get_users(firePl)
    users = usersResult.users
    for i in range(len(users)):
        text = text + users[i].display_name
        if i < len(users)-1: text = text + ", "
    print("MP, notistring done ", text)
    return text

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))