import httpx
from os import environ
from time import time
from asyncio import Lock
from cachetools import TTLCache
from myFunc import createTableApi

nUsers = environ['N_USERS']
pushAllUserLimit = 5000
pushAllReqHourLimit = 3
pushRandomReqhourLimit = 15
trafficLock = Lock()
traffInfo = {"req/h":0, "lastReq":time()}
wasPush = TTLCache(maxsize=1, ttl=250)
wasPush['fcm'] = True
hpx = httpx.AsyncClient(timeout=None)



async def decideMassPush(public):
    if not public: return 0
    if 'fcm' in wasPush:
        print("push break 4min not passed")
        return 0
    print(f"current traffic obj: {traffInfo}")
    async with trafficLock:
        reject = False
        if 'fcm' not in wasPush:
            timeNow = time()
            reqH = round(3600/(timeNow - traffInfo['lastReq']), 4)
            wasPush['fcm'] = True
            traffInfo['req/h'] = reqH
            traffInfo['lastReq'] = timeNow
        else: reject = "traffic was calc by one thread before, reject"
    if reject:
        print(reject)
        return 0

    userFak = round(pushAllUserLimit/nUsers, 4)
    print(f"new traffObj {traffInfo} userFactor {userFak}")

    if userFak > 1: userFak = 1
    if reqH == 0: randFak = userFak
    else:
        if reqH > pushRandomReqhourLimit: traffFak = 0
        else: traffFak = pushAllReqHourLimit/reqH
        print(f"traffic factor: {traffFak}")
        if traffFak > 1: traffFak = 1
        randFak = round(userFak * traffFak, 4)
    
    print(f"result factor: {randFak}")
    return randFak



async def getFcmReceivers(uid, receivers, public):
    if not public: return receivers
    res = await hpx.post(createTableApi +f'/GetFcmReceivers/{uid}', json=receivers)
    print(f"GetFcmReceivers Res: {res.status_code} {res.text}")
    if res.status_code == 200:
        FcmReceivers = res.json()
        print(f"FcmRecs type {type(FcmReceivers)} len {len(FcmReceivers)}")
        return FcmReceivers
    return receivers
