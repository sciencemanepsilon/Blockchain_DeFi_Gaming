from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request
badStrings = [None, "", "null", "undefined"]

class botUserRecord:
    def __init__(self, uid, nick, photo):
        self.uid = uid
        self.display_name = nick
        self.photo_url = photo

def getJWT(audience):
    auth_req = Request()
    jwt = fetch_id_token(auth_req, audience)
    print(f"tok for {audience}: {len(jwt)}")
    return jwt

def inputVali(ballance, rTimeout, public, device, media,
    betMin, invPlayers, coinAsUSD, minBetUSD, game, buyIn, videoFak, tid):

    if device in badStrings: return "invalid device Id"
    if tid in badStrings: return "invalid table Id"
    if not checkTypes([coinAsUSD, betMin, buyIn, ballance], float):
        if not checkTypes([coinAsUSD], int): return "invalid currencyAsUSD"
        if not checkTypes([betMin], int): return "invalid minimum bet"
        if not checkTypes([buyIn], int): return "invalid buy in"
        if not checkTypes([ballance], int): return "invalid wallet ballance"
    if not checkTypes([rTimeout, minBetUSD], int): return "invalid ints"
    if rTimeout < 5: return "invalid round timeout value"
    if media not in ["audio", "video", "no-media"]:
        return "invalid MediaMode"
    minBetTresh = minBetUSD/coinAsUSD
    if betMin < minBetTresh: return "insufficient minimum bet"
    if ballance < betMin: return "not enough money in wallet"
    if media == "video":
        if betMin < minBetTresh *videoFak:
            return "insufficient minimum bet for video"
        if ballance < betMin: return "not enough money for video table"
    if game == "pokerTournament_Tables":
        if buyIn < betMin *3: return "buyIn must be 3 times minBet"
        if ballance < buyIn: return "not enough money for poker tournament"
    if not isinstance(invPlayers, list): return "invalid invited players"
    if len(invPlayers) > 18: return "max invPlayers is 18"
    if len(invPlayers) < 1 and not public: return "table must be public"
    return False


def checkTypes(arr, objType):
    for ele in arr:
        if not isinstance(ele, objType): return False
    return True