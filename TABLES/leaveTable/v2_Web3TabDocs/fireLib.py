from uuid import uuid4
from transLib import calcBallanceAnd_cAfter, collNames

def validateInput(tableId, admin, playerCount, users, gameColl, mode):
    single = True
    if None in [tableId, admin, playerCount]: return "missing params",0,0
    if not users or not isinstance(users, list): return "users mustBeNonEmptyArray",0,0

    if not isinstance(users[0], dict): return "invalid users array ele",0,0
    if "uid" not in users[0].keys(): return "missing uid",0,0
    if users[0]['uid'] == admin and len(users) == 1: single = False
    if gameColl not in collNames: return "invalid gameColl",0,0

    for usDoc in users:
        user = usDoc['uid']
        kys = usDoc.keys()
        if "walletAddress" not in kys: return "missing wallet address",0,0
        if "hands" not in kys:
            return "missing wallet-field in users array",0,0
        if 'isWatcher' not in kys or 'gameJoinedAt' not in kys:
            return "invalid users object",0,0
        if len(usDoc['hands']) < 1:
            print(f"when {mode}, user {user} has empty hands array")
        else:
            for hand in usDoc['hands']:
                hkeys = hand.keys()
                if "action" not in hkeys: return "missing hand action",0,0
                if "amount" not in hkeys:
                    return "hand amount is missing",0,0
    return False, "Matic", single


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
    i, ERR, BqTranses, stats, actLogDate = (0, [], [], genStatsDict(currency), [])
    if len(hands) < 1:
        return i, BqTranses, iswatch, stats, ERR, actLogDate
    
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
        BqLog['fireId'], iswatch = str(uuid4()), hand['isWatcher']
        BqTranses.append(BqLog)
        actLogDate.append(actLog['date'])
        stats = clacStats(stats, actLog)
        print(f"user {uid} hand {i} {actLog['name']} amount {hand['amount']}")
        i = i + 1
    return i, BqTranses, iswatch, stats, ERR, actLogDate
