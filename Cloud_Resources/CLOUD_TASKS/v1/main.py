import uvicorn, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from Tasks import scheduleTask
from FcmModule import decideMassPush, getFcmReceivers
from myFunc import inviteFrParams, deleteInvitesParams, massPushParams
from myFunc import inGameInviteParams, getPrettyAndLink, valiInput, genMsgIds

app = FastAPI()
print(f"p1 {inviteFrParams} p2 {deleteInvitesParams}\nServer started")
massPushMasg = "{0} opened a {1} game, min.bet {2} {3}. Click to join!"
frTabOpenMsg = "Your friend {0} opended a {1} game, min.bet {2} {3}. Click to join!"
frInGameMsg = "Your friend {0} invited you to a {1} game, min.bet {2} {3}. Click to join!"



@app.post("/OnRoomCreate/{curr}/{public}/{adminUid}", response_class=PlainTextResponse)
async def crTabChildren(curr:str, public:bool, adminUid:str, request:Request):
    rd = await request.json()
    invitedPlayers, adminNick, minBet, link = (
        rd['invP'], rd['adminNick'], rd['minBet'], rd['link']
    )
    print(f"START: admin {adminNick} {link} invP {invitedPlayers}")
    #scheduleTask(*tGuardParams, {"col":gameCol, "tid":tid})

    err, col = valiInput(invitedPlayers, adminNick, link, minBet, curr, True)
    if err: return PlainTextResponse(content=err, status_code=200)

    gamePretty = getPrettyAndLink(col)
    MassPushMsg = massPushMasg.format(adminNick, gamePretty, minBet, curr)
    FrMsg = frTabOpenMsg.format(adminNick, gamePretty, minBet, curr)

    randFak, invitedPlayers = await asyncio.gather(
        decideMassPush(public), getFcmReceivers(adminUid, invitedPlayers, public)
    )
    print(f"randFak {randFak} invP {len(invitedPlayers)} {type(invitedPlayers)}")
    UniPayload = {"invP":invitedPlayers, "uid":adminUid, "link":link}

    if len(invitedPlayers) > 0:
        msgIds = genMsgIds(invitedPlayers)
        scheduleTask(*inviteFrParams, {**UniPayload, "msgIds":msgIds, "msg":FrMsg})
        scheduleTask(*deleteInvitesParams, {**UniPayload, "msgIds":msgIds})

    if randFak > 0:
        scheduleTask(*massPushParams, {**UniPayload, "msg":MassPushMsg, "randFak":randFak})
    print("End")
    return PlainTextResponse(content="success", status_code=200)




@app.post("/inGameInvites", response_class=PlainTextResponse)
async def ingameInvites(request: Request):
    rd = await request.json()
    link, adminNick, invitedPlayers, minBet, curr = (
        rd['link'], rd['invitorNick'], rd['invP'], rd['minBet'], rd['currency']
    )
    print(f"START: {adminNick} link {link} minBet {minBet} {curr} invP {invitedPlayers}")
    
    err, col = valiInput(invitedPlayers, adminNick, link, minBet, curr, False)
    if err: return PlainTextResponse(content=err, status_code=400)
    gamePretty = getPrettyAndLink(col)
    msg = frInGameMsg.format(adminNick, gamePretty, minBet, curr)

    UniPayload = {
        "invP":invitedPlayers, "link":link,
        "uid":adminNick, "msgIds":genMsgIds(invitedPlayers)
    }
    scheduleTask(*inGameInviteParams, {**UniPayload, "msg":msg})
    scheduleTask(*deleteInvitesParams, UniPayload)
    print("End")
    return PlainTextResponse(content="success", status_code=200)




@app.post("/CreateTask", response_class=PlainTextResponse)
async def noramlTask(request: Request):
    req = await request.json()
    url, inSec, payload, queName, region = (
        req.get('url'), req.get('insec'),
        req.get('payload'), req.get('queName'), req.get('region')
    )
    print(f"inSec {inSec} que {queName} region {region}")
    res = scheduleTask(url, inSec, queName, region, payload)
    print("End")
    if res: return PlainTextResponse(content=res, status_code=281)
    return PlainTextResponse(content="success", status_code=200)


@app.post("/BatchTasks", response_class=PlainTextResponse)
async def scheduleBatchTask(request: Request):
    tasksArr = await request.json()
    print("batch tasksArr len: ", len(tasksArr))
    rStatus = 200
    for aa in tasksArr:
        print("task: ", aa)
        res = scheduleTask(
            aa['url'], aa['insec'],
            aa['queName'], aa['region'], aa['payload']
        )
        if res: rStatus = 281
    print("End")
    return PlainTextResponse(content="done", status_code=rStatus)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)