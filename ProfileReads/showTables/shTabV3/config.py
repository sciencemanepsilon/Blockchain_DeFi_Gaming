from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request

def getJWT(audience):
    auth_req = Request()
    jwt = fetch_id_token(auth_req, audience)
    print(f"tok for {audience}: {len(jwt)}")
    return jwt

def genUserSnapsPerColl(tc):
    gamColls = {}
    for game in tc:
        linkArr = game['link'].split("/")
        gameInputKey = linkArr[1]
        gamColls[gameInputKey] = {}
        for coll in game.keys():
            if "_Tables" in coll:
                gamColls[gameInputKey][coll] = {}
    return gamColls


def getPrettyAndRoomLink(index, coll, tc):
    if coll in tc[index]:
        return tc[index][coll]['pretty'], tc[index]['link']
    return getPrettyAndRoomLink(index + 1, coll, tc)


def initRoomLink(beta, liveDom, ori,
    game, gamColls, isPlayer, viewMore):

    if ori in liveDom: domain = liveDom[0]
    elif ori == beta: domain = beta
    else: domain = ori
    if game not in gamColls: return True, 'invalid game'
    if isPlayer not in ["yes", "no"] or viewMore not in ["yes", "no"]:
        print("isPlayer or viewMore missing")
        return True, 'invalid view more or is player'
    return False, domain