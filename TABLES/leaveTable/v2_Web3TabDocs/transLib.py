from os import environ
from time import time
from httpx import Client
from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request
syncHpx = Client(timeout=None)

def getJWT(audience):
    auth_req = Request()
    jwt = fetch_id_token(auth_req, audience)
    print(f"tok for {audience}: {len(jwt)}")
    return jwt

data = syncHpx.get(
    environ['SYS_CONFIG_API'], params={"oriApi":"LeaveTable"},
    headers={"Authorization":f"Bearer {getJWT(environ['SYS_CONFIG_API'])}"}
).json()

collNames, beta, live, blockApi, topicPath = (
    data['Transes']['FromOri'], data['beta'],
    data['live'], data['blockApi'],
    "projects/weje-2023/topics/LeaveTable"
)
feeFaktor, specialHandTrans, handWins, handLosses = (
    data['Transes']['feeFactor'],
    data['Transes']['Names']['Special'],
    data['Transes']['Names']['handWins'],
    data['Transes']['Names']['handLosses']
)
asyncHpx = {"age":time(), "token":getJWT(blockApi)}


def callContract(tid, plArr, tries):
    diff = round((time() -asyncHpx['age'])/60,2)
    if diff > 55:
        asyncHpx['token'] = getJWT(blockApi)
        asyncHpx['age'] = time()
        print(f"token too old: {diff} minutes, new jwt set")
    headers = {"Authorization":f"Bearer {asyncHpx['token']}"}
    #headers = setNewHttpxClient(headers)
    try:
        return syncHpx.post(
            blockApi +"/ContractFunc", headers=headers,
            json={"funcName":"leaveGame", "tid":tid, "playersArr":plArr}
        )
    except Exception as e:
        print(f"contract call failed: {e}")
        if str(e) == "Event loop is closed":
            #if tries > 1: return 500
            #return await callContract(tid, plArr, tries + 1)
            return 280
        return 500


"""def setNewHttpxClient(headers):
    if not asyncHpx['hpx']:
        headers['Connection'] = "close"
        asyncHpx['hpx'] = AsyncClient(timeout=None)
        print("setting new httpx client with close header")
    else: print("not setting new httpx client")
    return headers"""


def calcFee(amount):
    if 0 in [amount, feeFaktor]: return 0
    return amount * feeFaktor

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
        fee = calcFee(amount)
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