import os, requests
from Tasks import checkSess
from flask import Flask, request, jsonify
from firebase_admin import firestore, initialize_app, auth
from myFunc import notiContents, initRoomLink, decideMassPush
from myFunc import traffInfo, updateTrafficInfo
from valid import inputVali, botUserRecord, getJWT
app = Flask(__name__)

res = requests.get(
    os.environ['SYS_CONFIG_API'], params={"oriApi":"CreateTable"},
    headers={"Authorization":f"Bearer {getJWT(os.environ['SYS_CONFIG_API'])}"}
).json()

initialize_app()
db = firestore.client()
Bearer = {"jwt":None, "age":None}
beta, liveDom, coinNamesDict, videoFak, bo, tc, taskCaller = (
    res['api_urls']['beta'], res['api_urls']['live'],
    res['coinNamesDict'], res['videoFak'], res['BotRecord'],
    res['tableConfig'], res['api_urls']['taskCallerApi']
)
bot = botUserRecord(bo['uid'], bo['nick'], bo['photo'])


@app.route('/openTable', methods=['POST'])
def createTable():
    ori = request.headers.get('ori')
    uid = request.headers.get('uid')
    device = request.headers.get('device')
    
    game, betMin, ballance, coinName, buyIn, rTimeout, public = (
        request.json.get('game'), request.json.get('betMin'),
        request.json.get('ballance'), request.json.get('coinName'),
        request.json.get('buyIn'), request.json.get('rTimeout'),
        request.json.get('public')
    )
    tid, invPlayers, media, fromQue = (
        request.json.get('tid'),
        request.json.get('invPlayers'),
        request.json.get('media'), request.json.get('fromQue')
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
        ballance, rTimeout, public, device, media, betMin,
        invPlayers, coinUSD, minBetUSD, game, buyIn, videoFak, tid
    )
    if msg:
        print(msg); return msg, 283

    if not fromQue: currUser = auth.get_user(uid)
    else: currUser = auth.get_user(uid)
    print(f"ballance {ballance} {coinName}")

    if not fromQue:
        print("checking Sess..")
        usDoc = db.document(f"users/{currUser.uid}").get().to_dict()
        err, jsonObj = checkSess(usDoc, device, roomLink)
        print(f"checkSession Res: err {err}, {jsonObj}")
        if err == 1:
            print(jsonObj); return jsonObj, 284
        if err:
            print(jsonObj['error'], " ,End")
            return jsonify(jsonObj), 222

    updateTrafficInfo()
    if len(invPlayers) > 0:
        notiText = "You invited "
        if fromQue: notiText = "We notified "
        notiText = createNoti(notiText, invPlayers)
    else: notiText = ""
    ww = notiContents(
        currUser.display_name, gamePretty,
        notiText, buyIn, fromQue, coinName
    )
    if fromQue:
        print("signal to client to create a new game, End")
        return jsonify({
            "error":"no error",
            "game":game, "msg":"Quick Match! Create a game"
        }), 200
        
    meineId = tid
    print(f"opened new table {meineId}, fromQue: {fromQue}")
    
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
    db.document(f"users/{currUser.uid}").update({
        u"Session.status": f"lobby-{game}-{meineId}"})
    print("End")
    return jsonify({
        "error":"no error",
        "link":roomLink + meineId + "&gameCollection=" + game
    }), 200



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