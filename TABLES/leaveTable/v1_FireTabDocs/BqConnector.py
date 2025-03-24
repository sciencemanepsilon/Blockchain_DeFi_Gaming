import json
from datetime import datetime
from asyncio import sleep
#from google.cloud import pubsub_v1
from transLib import topicPath
from fireLib import parseHands, updateUserSession, remUserFromTab
# publisher = pubsub_v1.PublisherClient()

def genValues(ress):
    dat, ERR, plArr = ([],[],[])
    for ele in ress:
        if ele[0]: dat.append(ele[0])
        if ele[1]: ERR.append(ele[1])
        if ele[2]: plArr.append(ele[2])
    return dat, ERR, plArr

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


def genJsonString(dat):
    preDat = {}
    for dd in dat:
        kys = list(dd.items())
        preDat[kys[0][0]] = kys[0][1]
    return json.dumps(preDat)


def triggerPubsub(msg, playersStringDict):
    """try:
        future = publisher.publish(topicPath, msg.encode("utf-8"), **playersStringDict)
        print(f"pubsub call {future.result()}")
    except Exception as e: print(f"pubsub call failed: {e}")"""
    return 0


async def userArr(user, gameColl, tableId, currency, single):
    await sleep(0)
    uid, res = (user['uid'], 0)
    print("got user", uid)
    j, BqTranses, iswatch, stats, ERR = parseHands(
        user['hands'], gameColl, tableId, uid, user['isWatcher'], currency
    )
    updateUserSession(uid, gameColl, tableId)
    if single:
        rmUserParam = u"players"
        if iswatch: rmUserParam = u"watchers"
        remUserFromTab(tableId, rmUserParam, uid)
    
    if len(BqTranses) > 0:
        erg = valiStats(user['gameJoinedAt'], user['gameLeaveAt'], stats)
        if erg != False:
            res = {uid:{
                "tra":BqTranses,
                "sta":{"col":gameColl, "hours":erg, "stats":stats}
            }}
    print(f"hand {j} done, watcher {iswatch}, BqTranses {len(BqTranses)}")
    return res, ERR, uid