from datetime import datetime
from asyncio import sleep
from google.cloud import pubsub_v1
from fireLib import parseHands
from transLib import topicPath, noWeb3callOnFinishHandColls
publisher = pubsub_v1.PublisherClient()

def valiStats(gameJoinedAt, gameLeaveAt, stats):
    print("vali stats: ", stats)
    if not stats or len(stats) < 2: return False
    t1 = datetime.fromisoformat(gameJoinedAt[:-1]).timestamp()
    t2 = datetime.fromisoformat(gameLeaveAt[:-1]).timestamp()
    return round((t2 - t1)/3600, 4)


def triggerPubsub(msg, playersStringDict):
    try:
        future = publisher.publish(topicPath, msg.encode("utf-8"), **playersStringDict)
        print(f"pubsub call {future.result()}")
    except Exception as e: print(f"pubsub call failed: {e}")
    return 0


async def userArr(user, gameColl, tableId, currency):
    await sleep(0)
    uid, res = (user['uid'], 0)
    print(f"got user {uid}, hands {user['hands']}")

    j, BqTranses, iswatch, stats, traDates = parseHands(
        user['hands'], gameColl, tableId, uid, user['isWatcher'], currency
    )
    erg = valiStats(user['gameJoinedAt'], user['gameLeaveAt'], stats)
    print("vali stats RES: ", erg)
    hours, staPass = (erg, {**stats})
    if erg == False: hours, staPass = (None, None)
    res = {uid:{
        "tra":BqTranses, "transHistDates":traDates,
        "sta":{"col":gameColl, "hours":hours, "stats":staPass}
    }}
    # Affiliate:
    affi = 0
    if user['affiliate']:
        if gameColl in noWeb3callOnFinishHandColls:
            OurRevenue = user['coinsBeforeJoin'] - user['wallet']
            if OurRevenue > 0:
                affi = {"Uid":uid, "Aid":user['affiliate'], "TxVol":OurRevenue}
        else: affi = {"Uid":uid, "Aid":user['affiliate'], "TxVol":None}
    print(f"hand {j} done, Affiliate {affi} BqTranses {len(BqTranses)} stats {staPass}")
    return res, genWinLoseAmount(stats, uid, user['walletAddress'], gameColl, user['wallet']), affi


def genWinLoseAmount(sta, uid, wAddress, gameColl, ballance):
    sWin, sLose = (0,0)
    rDict = {"walletAddress":wAddress, "playerId":uid}
    if gameColl in noWeb3callOnFinishHandColls:
        return {
            **rDict, "isWon":False,
            "wallet": str(int(ballance*10**18))
        }
    if 'game win' in sta: sWin = sum(sta['game win'])
    if 'game lose' in sta: sLose = sum(sta['game lose'])
    if sWin > 0 and sLose > 0:
        if sWin == sLose:
            rDict['isWon'] = False
            rDict['wallet'] = 0
            return rDict
        rDict['wallet'] = str(int((sWin -sLose)*10**18))
        if rDict['wallet'] > 0: rDict['isWon'] = True
        else:
            rDict['isWon'] = False
            rDict['wallet'] = -1 *rDict['wallet']
        return rDict
    if sWin == 0 and sLose == 0:
        rDict['isWon'] = False
        rDict['wallet'] = 0
        return rDict
    if sWin > 0:
        rDict['isWon'] = True
        rDict['wallet'] = str(int(sWin*10**18))
        return rDict
    if sLose > 0:
        rDict['isWon'] = False
        rDict['wallet'] = str(int(sLose*10**18))
        return rDict