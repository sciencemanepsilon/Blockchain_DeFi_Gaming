from re import search
from os import environ
from json import loads
from uuid import uuid4

createTableApi = environ['CREATE_TABLE_API']
pid = environ['GOOGLE_CLOUD_PROJECT']
gamConfArr = loads(environ['GameConfigArray'])
allowOris = environ['ALLOWED_ORIGINS'].split("||")
requestTimeoutForAllTasks = int(environ['TASK_REQUEST_TIMEOUT'])

def genCollData():
    gamCollObj = {}
    for obj in gamConfArr:
        link = obj['link']
        for keyy in obj.keys():
            if "_Tables" in keyy:
                gamCollObj[keyy] = [obj[keyy]['pretty'], link]
    return gamCollObj

gameCollData = genCollData()
MASS_PUSH_URL = environ['MASS_PUSH_CL_TASK_URL']
GAME_INVITES_URL = environ['GAME_INVITES_CL_TASK_URL']
GAME_INVITES_AND_MASS_PUSH_QUE = environ['SEND_GAME_INVITES_CL_TASK_QUE']
CL_TASK_REGION = environ['GAME_INVITES_CL_TASK_REGION']

inGameInviteParams = [
    GAME_INVITES_URL,
    int(environ['INGAME_INVITES_CL_TASK_DELAY']),
    GAME_INVITES_AND_MASS_PUSH_QUE,
    CL_TASK_REGION
]
inviteFrParams = [
    GAME_INVITES_URL,
    int(environ['CR_TABLE_INVITES_CL_TASK_DELAY']),
    GAME_INVITES_AND_MASS_PUSH_QUE,
    CL_TASK_REGION
]
deleteInvitesParams = [
    GAME_INVITES_URL,
    int(environ['DELETE_GAME_INVITES_CL_TASK_DELAY']),
    environ['DELETE_GAME_INVITES_CL_TASK_QUE'],
    CL_TASK_REGION
]
massPushParams = [
    MASS_PUSH_URL,
    int(environ['CR_TABLE_MASS_FCM_CL_TASK_DELAY']),
    GAME_INVITES_AND_MASS_PUSH_QUE,
    CL_TASK_REGION
]
"""tGuardParams = {
    "url":res['queParams'][0]['url'],
    "firstDelay":res['queParams'][0]['insec'],
    "region":res['region'], "que":res['queParams'][0]['que']
}"""

def genMsgIds(invitedPlayers):
    msgIds = []
    for uid in invitedPlayers:
        aa = str(uuid4()).split("-")
        msgIds.append(f"{aa[0]}-{aa[3]}-{aa[4]}")
    return msgIds


def valiInput(invP, adminNick, link, minBet, curr, isCrTab):
    try:
        proto, url = link.split("//")
        ori, servName, params = url.split("/")
        tidKey, preTid, gameCol = params.split("=")
        tid, gameCollKey = preTid.split("&")
    except:
        print("invalid game link, End")
        return "invalid game link",0
    
    if tidKey not in {"?tableid", "index.html?tableid"} or gameCollKey != "gameCollection":
        print("invalid tidKey or gameColKey, End")
        return "invalid tik or gck",0
    if not isinstance(invP, list) or len(invP) > 10:
        print("invalid invP array, End")
        return "invalid invP array",0
    if not isCrTab and not invP:
        print("inGameInvP empty, End")
        return "must invite players",0
    if not adminNick or not minBet or curr not in {"POL", "WEJE"}:
        print("missing nick or minBet or curr, End")
        return "missing nick or minBet or curr",0
    if gameCol not in gameCollData:
        print("invalid gameColl: ", gameCol, ", End")
        return "invalid gameColl",0
    if f'{proto}//{ori}' not in allowOris:
        if not search(allowOris[-1], ori):
            print(f"invalid ori {ori}, End")
            return "invalid origin",0
    return False, gameCol


def getPrettyAndLink(col):
    return gameCollData[col][0]
