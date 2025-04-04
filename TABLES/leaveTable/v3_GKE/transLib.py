import httpx
from os import environ
from json import loads

def getFeeFak(url, route):
    try: errg = httpx.get(url + route).json()
    except Exception as e:
        print(f"getCommRate call failed: {e}")
        return 0.01
    try: print(f"feeFak {errg['commissionRate']} {type(errg['commissionRate'])}")
    except Exception as e:
        print(f"getCommRate error: {e}")
        return 0.01
    return errg['commissionRate']/100

def genWeb3config(colDict, getCommRoute):
    noWeb3OnFinishHand = set()
    res, poke, ludo, web3poker, web3bj, web3ludo = (
        {}, -9, -9, environ['BLOCKCHAIN_API'],
        environ['BLOCKCHAIN_API_BLACKJACK'], environ['BLOCKCHAIN_API_LUDO']
    )
    for col in colDict.keys():
        if "_Tables" not in col: continue
        if "poker" in col:
            if poke == -9: poke = getFeeFak(web3poker, getCommRoute)
            res[col] = {"web3url":web3poker, "fee":poke}
        if col == "BlackJack_Tables":
            noWeb3OnFinishHand.add(col)
            res[col] = {"web3url":web3bj, "fee":0}
        if "Ludo" in col:
            if ludo == -9: ludo = getFeeFak(web3ludo, getCommRoute)
            res[col] = {"web3url":web3ludo, "fee":ludo}
    return res, noWeb3OnFinishHand

topicPath, db_pfx, specialHandTrans, handWins, handLosses = (
    environ['LEAVETAB_TOPIC_PATH'], environ['DB_COLL_PREFIX'],
    set(environ['SPECIAL_TX'].split("-")), set(environ['WIN_TX'].split("-")),
    set(environ['LOSE_TX'].split("-"))
)
web3Config, noWeb3callOnFinishHandColls = genWeb3config(
    loads(environ['PRETTY_TX_ORIs']), environ['getCommRateRoute']
)
syncHpx = httpx.AsyncClient(timeout=1200)
print(f"init envs: topic {topicPath} pfx {db_pfx} web3Config {web3Config}")



async def contractGameById(tid, gameColl):
    route = f"{environ['getGameByIdRoute']}/{tid}"
    res = await syncHpx.get(web3Config[gameColl]['web3url'] + route)
    print(f"web3 GetGamByIdRes {res.status_code}")
    if res.status_code == 200:
        res = res.json()
        return res['game']
    return res.status_code

async def callContract(tid, plArr, gameColl):
    try:
        return await syncHpx.post(
            web3Config[gameColl]['web3url'] + environ['contractFuncRoute'],
            json={"funcName":"leaveGame", "tid":tid, "playersArr":plArr}
        )
    except Exception as e:
        print(f"contract call failed: {e}")
        if str(e) == "Event loop is closed": return 280
        return 500

def calcFee(amount, col):
    if 0 in {amount, web3Config[col]['fee']}: return 0
    return amount * web3Config[col]['fee']


def calcBallanceAnd_cAfter(coll, hand, tid, usid, currency):
    try: act = hand['action'].replace("-", " ")
    except: return "missingDash in action", {},{}
    if hand['amount'] == 0:
        if act not in specialHandTrans: return "zero amount", {},{}
    
    if act not in handLosses and act not in handWins and act not in specialHandTrans:
        print(f"not supported action: {act} for {usid}")
        return "handResult not identified", {},{}
    
    amount, fee = (hand['amount'], 0)
    if act in handWins:
        fee = calcFee(amount, coll)
        amount = round(amount - fee, 4)

    actLog, BqLog = makeActLog(act, coll, tid, usid, hand['date'], amount, fee, currency)
    return "no error", actLog, BqLog


def makeActLog(act, coll, tid, usid, date, amount, fee, currency):
    actLog = {
        u"name":act , u"from":coll,
        u"from-id":tid, u"to":usid, u"date":date,
        u"amount":amount, u"fee":fee, u"currency":currency
    }
    BqLog = {
        "uid":usid, "name":act,
        "from":coll, "fireId":None, "currency":currency,
        "fromId":tid, "to":usid, "coinAm":amount, "fee":fee
    }
    return actLog, BqLog