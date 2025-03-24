def initRoomLink(game, ori, tc, lbOri, Referer):
    if lbOri: domain =  rmTrailingSlash(lbOri)
    elif Referer: domain = rmTrailingSlash(Referer)
    elif ori: domain = rmTrailingSlash(ori)
    else: return False, 'invalid origin',0,0
    if game not in tc: return False, 'invalid game',0,0
    try: return True, domain + tc[game]['roomLink'], tc[game]['pretty'], tc[game]['minBetUSD']
    except: return False, 'invalid game input',0,0

def rmTrailingSlash(url):
    if url[-1] == "/": return url[:-1]
    return url

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

def genTabConfig(att):
    tc = {}
    for ele in att:
        for eleKey in ele.keys():
            if "_Tables" in eleKey:
                tc[eleKey] = {
                    "roomLink": ele['link'],
                    "pretty": ele[eleKey]['pretty'],
                    "minBetUSD": ele[eleKey]['qMinBet']
                }
    return tc