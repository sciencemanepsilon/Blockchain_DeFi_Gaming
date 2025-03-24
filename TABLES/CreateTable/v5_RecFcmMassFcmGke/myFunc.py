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