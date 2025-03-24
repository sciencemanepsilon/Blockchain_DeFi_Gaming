from time import time
traffInfo = {
    "req/h": 0, "reqTotal": 0,
    "lastReq": None, "firstReq": None, "AveReq/h": 0
}

def updateTrafficInfo():
    print(f"current traffic obj: {traffInfo}")
    traffInfo['reqTotal'] = traffInfo['reqTotal'] + 1
    timeNow = time()

    if traffInfo['lastReq'] != None:
        traffInfo['req/h'] = round(3600/(timeNow - traffInfo['lastReq']), 2)
        traffInfo['AveReq/h'] = round((3600*traffInfo['reqTotal'])/(timeNow - traffInfo['firstReq']), 2)
    else: traffInfo['firstReq'] = timeNow
    
    traffInfo['lastReq'] = timeNow
    print(f"new traffic obj: {traffInfo}")
    return 0

def decideMassPush(reqH, nUsers, userLim, allReqHLimit, randomReqHLimit):
    userFak = round(userLim/nUsers, 4)
    print(f"user factor: {userFak}")
    if userFak > 1: userFak = 1

    if reqH == 0: randFak = userFak
    else:
        if reqH > randomReqHLimit: traffFak = 0
        else:
            traffFak = allReqHLimit/reqH
        print(f"traffic factor: {traffFak}")
        if traffFak > 1: traffFak = 1

        randFak = round(userFak * traffFak, 4)
    
    print(f"result factor: {randFak}")
    return randFak


def initRoomLink(game, beta, liveDom, ori, att):
    roomLink, minBetUSD = (None, 0)
    if ori in liveDom: domain = liveDom[0]
    elif ori == beta: domain = beta
    else: domain = ori
    for ele in att:
        if game in ele.keys():
            seats = ele['seats']
            minBetUSD = ele[game]['qMinBet']
            roomLink = domain + ele['link']
            pretty = ele[game]['pretty']
            break
    if not roomLink: return False, 'invalid game input',0,0,0
    return True, roomLink, minBetUSD, seats, pretty


def notiContents(nick, game, x, buyIn, fromQue, currency):
    insert = ""
    if game == "Poker Tournament": insert = f"{buyIn} {currency}"
    if not fromQue:
        ww = {
            "msg": f"{nick} invited you to a {insert} {game} game. Click to join the game!",
            "msg2": f"{x} to a {insert} {game} game.",
            "massPush": f"{nick} opened a {insert} {game} table. Click to join!"}
    else:
        ww = {
            "msg": f"You've got a {insert} {game} Match. Click to play!",
            "msg2": f"{x} to join the {insert} {game} table",
            "massPush": f"{nick} opened a {insert} {game} table. Click to join!"}
    return ww

