from uuid import uuid4
from transLib import calcBallanceAnd_cAfter, web3Config, contractGameById

def getUidsFromDictArr(arr, targetKey):
    return [pl[targetKey] for pl in arr]

def getWeb3pl(tableId, users, coll):
    pres = contractGameById(tableId, coll)
    if not pres or pres == 500: return getUidsFromDictArr(users, "uid")
    return getUidsFromDictArr(pres['players'], "playerId")


def validateInput(tableId, admin, playerCount, users, gameColl, mode):
    single = True
    if None in {tableId, admin, playerCount}: return "missing params",0,0
    if not users or not isinstance(users, list): return "users mustBeNonEmptyArray",0,0
    if not isinstance(users[0], dict): return "invalid users array ele",0,0
    if "uid" not in users[0]: return "missing uid",0,0
    if gameColl not in web3Config: return "invalid gameColl",0,0
    if playerCount == 1 or len(users) > 1: single = False
    if single or len(users) > 1: players = getWeb3pl(tableId, users, gameColl)
    else: players = []

    for usDoc in users:
        user = usDoc['uid']
        kys = usDoc.keys()
        if "affiliate" not in kys: return "missing affiliate key",0,0
        if "walletAddress" not in kys: return "missing wallet address",0,0
        if "hands" not in kys:
            return "missing wallet-field in users array",0,0
        if 'isWatcher' not in kys or 'gameJoinedAt' not in kys:
            return "invalid users object",0,0
        print(f"when {mode}, user {user} has hands: {usDoc['hands']}")
    return False, single, players



def clacStats(sta, tra):
    act = tra['name']
    LvCoins = tra['amount']
    specialF = ["game draw", "audio game", "video game"]
    if act in specialF:
        if act in sta: sta[act] = sta[act] + 1
        else: sta[act] = 1
        return sta
    if act == "buy item":
        sta[act]['prices'].append(LvCoins)
        sta[act]['names'].append(tra['from-id'])
        return sta
    # game win/lose:
    if act in sta: sta[act].append(LvCoins)
    else: sta[act] = [LvCoins]
    return sta


def parseHands(hands, gameColl, tableId, uid, iswatch, currency):
    i, BqTranses, stats, actLogDate = (1, [], {"currency":currency}, [])
    if len(hands) < 1:
        print("empty hand")
        return i, BqTranses, iswatch, stats, actLogDate
    
    print(f"hands {len(hands)} gam {gameColl}")
    for hand in hands:
        error, actLog, BqLog = calcBallanceAnd_cAfter(
            gameColl, hand, tableId, uid, currency
        )
        if error != "no error":
            print(error)
            continue
        BqLog['fireId'], iswatch = str(uuid4()), hand['isWatcher']
        BqTranses.append(BqLog)
        actLogDate.append(actLog['date'])
        stats = clacStats(stats, actLog)
        print(f"user {uid} hand {i} amount {hand['amount']} stats {stats}")
        i = i + 1
    return i, BqTranses, iswatch, stats, actLogDate
