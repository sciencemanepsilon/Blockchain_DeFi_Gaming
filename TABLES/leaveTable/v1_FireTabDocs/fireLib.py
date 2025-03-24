from firebase_admin import initialize_app, firestore
from transLib import calcBallanceAnd_cAfter, collNames
initialize_app()
db = firestore.client()

def validateInput(tableId, admin, playerCount, users, gameColl, mode):
    single = True
    if None in [tableId, admin, playerCount]: return "missing params",0,0
    if not users or not isinstance(users, list): return "users mustBeNonEmptyArray",0,0

    if not isinstance(users[0], dict): return "invalid users array ele",0,0
    if "uid" not in users[0].keys(): return "missing uid",0,0
    if len(users) > 1: single = False
    elif users[0]['uid'] == admin: single = False
    if gameColl not in collNames: return "invalid gameColl",0,0

    try: tableDoc = db.document(f"tables/{tableId}").get().to_dict()
    except: return "coll and/or tableId not exist",0,0
    if tableDoc['game'] != gameColl: return 'coll mismatch',0,0

    for usDoc in users:
        try: user = usDoc['uid']
        except: return "missing uid",0,0
        if user not in tableDoc['players'] and user not in tableDoc['watchers']:
            return 'missing users in players array',0,0
        kys = usDoc.keys()
        if "hands" not in kys:
            return "missing wallet-field in users array",0,0
        if 'isWatcher' not in kys or 'gameJoinedAt' not in kys:
            return "invalid users object",0,0
        if len(usDoc['hands']) < 1:
            if mode == "duringHand": return "zero hands in duringHand",0,0
        else:
            for hand in usDoc['hands']:
                hkeys = hand.keys()
                if "action" not in hkeys: return "missing hand action",0,0
                if tableDoc['table']['status'] == "lobby":
                    if hand['action'] in ["game-win","game-lose"]:
                        print("win or lose in lobby mode")
                if "amount" not in hkeys:
                    return "hand amount is missing",0,0
    if single and user == admin:
        if len(tableDoc['players']) > 1:
            return 'admin leave before others forbidden',0,0
    if single:
        return makePlString(tableDoc['players']), tableDoc['currency'], single
    return "null", tableDoc['currency'], single


def makePlString(players):
    plStr, ii = (players[0], 0)
    for player in players:
        if ii > 0: plStr = plStr + "-" + player
        ii = ii + 1
    print(f"len pl arr {len(players)} playersStr {plStr}")
    return plStr

def genStatsDict(currency):
    return { 
        "currency":currency,
        "game win":[], "game lose":[],
        "game draw":0, "audio game":0, "video game":0,
        "buy item":{"prices":[], "names":[]},
        "win as watcher":[], "lose as watcher":[]
    }

def clacStats(sta, tra):
    act = tra['name']
    LvCoins = tra['amount']
    specialF = ["game draw", "audio game", "video game"]
    if act in specialF:
        sta[act] = sta[act] + 1
        return sta
    if act == "buy item":
        sta[act]['prices'].append(LvCoins)
        sta[act]['names'].append(tra['from-id'])
        return sta
    sta[act].append(LvCoins)
    return sta


def parseHands(hands, gameColl, tableId, uid, iswatch, currency):
    i, ERR, BqTranses = (0, [], [])
    if len(hands) < 1:
        return i, BqTranses, iswatch, {}, ERR
    
    batch = db.batch()
    stats = genStatsDict(currency)
    print(f"hands {len(hands)} gam {gameColl}")
    for hand in hands:
        if hand['amount'] < 0:
            ERR.append("negative hand")
            print("correcting negtive hand amount")
            hand['amount'] = -1 * hand['amount']

        error, actLog, BqLog = calcBallanceAnd_cAfter(
            gameColl, hand, tableId, uid, currency
        )
        if error != "no error":
            print(error)
            ERR.append(error)
            continue

        iswatch = hand['isWatcher']
        transRef = db.collection(f"users/{uid}/Transactions").document()
        BqLog['fireId'] = transRef.id
        BqTranses.append(BqLog)
        batch.set(transRef, actLog)
        stats = clacStats(stats, actLog)
        print(f"user {uid} hand {i} {actLog['name']} amount {hand['amount']}")
        i = i + 1
    if i < 1: return i, BqTranses, iswatch, stats, ERR
    batch.commit()
    return i, BqTranses, iswatch, stats, ERR


def updateUserSession(user, gameColl, tableId):
    sess = db.document(f"users/{user}").get().to_dict()['Session']
    print("got sess: ", sess['status'])
    if tableId in sess['status']:
        print("sess is good, updating to online..")
        db.document(f"users/{user}").update({u"Session.status":"online"})
    else: print("ERROR: sess not good")
    return 0


def remUserFromTab(tid, field, uid):
    db.document(f"tables/{tid}").update({field: firestore.ArrayRemove([uid])})
    return 0

def cleanAll(tableId):
    """db.document(f"tables/{tableId}").update({
        u'table.admin':"", u'table.status':'empty',
        u'table.isGameFinished': False, u'table.isGameStarted': False,
        u"table.name":None, u"table.scheduled":None, u'players':[],
        u"table.openDate": None, u"watchers": [], u"invPlayers": []
    })"""
    db.document(f"tables/{tableId}").delete()
    return 0