badStrings = frozenset([None, "", "null", "undefined", "object Object"])

class botUserRecord:
    def __init__(self, uid, nick, photo):
        self.uid = uid
        self.display_name = nick
        self.photo_url = photo

def inputVali(ballance, rTimeout, public, device, media,
    betMin, invPlayers, coinAsUSD, minBetUSD, game, buyIn, videoFak, tid):

    if device in badStrings: return "invalid device Id"
    if tid in badStrings: return "invalid table Id"
    #if not checkTypes([coinAsUSD, betMin, buyIn, ballance], float):
        #if not checkTypes([coinAsUSD], int): return "invalid currencyAsUSD"
        #if not checkTypes([betMin], int): return "invalid minimum bet"
        #if not checkTypes([buyIn], int): return "invalid buy in"
        #if not checkTypes([ballance], int): return "invalid wallet ballance"
    #if not checkTypes([rTimeout, minBetUSD], int): return "invalid ints"
    if rTimeout < 5: return "invalid round timeout value"
    if media not in {"audio", "video", "no-media"}:
        return "invalid MediaMode"
    """minBetTresh = minBetUSD/coinAsUSD
    if betMin < minBetTresh: return "insufficient minimum bet"
    if ballance < betMin: return "not enough money in wallet"
    if media == "video":
        if betMin < minBetTresh *videoFak:
            return "insufficient minimum bet for video"
        if ballance < betMin: return "not enough money for video table"
    if game == "pokerTournament_Tables":
        if buyIn < betMin *3: return "buyIn must be 3 times minBet"
        if ballance < buyIn: return "not enough money for poker tournament"
    """
    if not isinstance(invPlayers, list): return "invalid invited players"
    if len(invPlayers) > 20: return "max invPlayers is 18"
    if len(invPlayers) < 1 and not public: return "You must invite friends to a private table"
    return False

def checkTypes(arr, objType):
    for ele in arr:
        if not isinstance(ele, objType): return False
    return True

def checkSess(usDoc, device, roomLink):
    if usDoc['Session']['device'] != device:
        return 1, "user logged with other device"
    if "-" in usDoc['Session']['status']:
        tInfo = usDoc['Session']['status'].split("-")
        return 2, {
            'error':'User inGame',
            'link':roomLink +tInfo[2] +"&gameCollection=" +tInfo[1]
        }    
    if "?" in usDoc['Session']['status']:
        return 3, {
            'error':'user in Que',
            'msg':'Please exit the Quickmatch-Que to create a table'
        }
    print("checkSess skipped")
    return 0, None