from datetime import datetime
from asyncio import sleep
from google.cloud import pubsub_v1
from fireLib import parseHands
from transLib import topicPath
publisher = pubsub_v1.PublisherClient()

def fetchStats(stats):
    gWin = stats["game win"]
    gLose = stats["game lose"]
    wWin = stats["win as watcher"]
    wLose = stats["lose as watcher"]
    audio = stats["audio game"] #num
    gDraw = stats["game draw"]
    video = stats["video game"] #num
    #stats[buy item]:dict -> {prices:[], names:[]}
    return gWin, gLose, wWin, wLose, audio, video, gDraw


def valiStats(gameJoinedAt, gameLeaveAt, stats): 
    if not stats: return False
    gWin, gLose, wWin, wLose, audio, video, gDraw = fetchStats(stats)
    maxStatsSum = len(gWin) + len(gLose) + len(wWin) + len(wLose) + gDraw
    mediaSum = audio + video
    buyStatsSum = len(stats["buy item"]["names"])
    print(f"games {maxStatsSum} media {mediaSum} Nbuy {buyStatsSum}")
    if mediaSum + maxStatsSum + buyStatsSum < 1:
        return False
    t1 = datetime.fromisoformat(gameJoinedAt[:-1]).timestamp()
    t2 = datetime.fromisoformat(gameLeaveAt[:-1]).timestamp()
    return round((t2 - t1)/3600, 4)


def triggerPubsub(msg, playersStringDict):
    try:
        future = publisher.publish(topicPath, msg.encode("utf-8"), **playersStringDict)
        print(f"pubsub call {future.result()}")
    except Exception as e: print(f"pubsub call failed: {e}")
    return 0


async def userArr(user, gameColl, tableId, currency, single):
    await sleep(0)
    uid, res = (user['uid'], 0)
    print("got user", uid)
    j, BqTranses, iswatch, stats, ERR, traDates = parseHands(
        user['hands'], gameColl, tableId, uid, user['isWatcher'], currency
    )
    erg = valiStats(user['gameJoinedAt'], user['gameLeaveAt'], stats)
    hours, staPass = (None, None)
    if erg != False: hours, staPass = (erg, stats)
    res = {uid:{
        "tra":BqTranses, "transHistDates":traDates,
        "sta":{"col":gameColl, "hours":hours, "stats":staPass}
    }}
    print(f"hand {j} done, watcher {iswatch}, BqTranses {len(BqTranses)}")
    return res, ERR, genWinLoseAmount(stats, uid, user['walletAddress'])


def genWinLoseAmount(sta, uid, wAddress):
    rDict = {"walletAddress":wAddress, "playerId":uid}
    sWin = sum(sta['game win'])
    sLose = sum(sta['game lose'])
    if sWin > 0 and sLose > 0:
        if sWin == sLose:
            rDict['isWon'] = False
            rDict['wallet'] = 0
            return rDict
        rDict['wallet'] = int((sWin -sLose)*10**18)
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
        rDict['wallet'] = int(sWin*10**18)
        return rDict
    if sLose > 0:
        rDict['isWon'] = False
        rDict['wallet'] = int(sLose*10**18)
        return rDict