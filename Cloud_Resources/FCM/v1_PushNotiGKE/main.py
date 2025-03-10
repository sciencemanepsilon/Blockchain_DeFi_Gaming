import uvicorn
from os import environ
from typing import Annotated
from fastapi import FastAPI, Response, Header, Request
from FireLib import exeAddFcm, exeUnsubscribeFCM
from FireLib import inputVali, getUnr, sendfcmm, sendMulti

app = FastAPI()
default_cAction = environ['FCM_DEFAULT_CLICK_ACTION']


@app.get('/Manage/{uid}')
async def ManageFcmDevice(
    uid:str, fcm:Annotated[str, Header()],
    device:Annotated[str, Header()], RemDevice:Annotated[str, Header()]):

    print(f"START: uid {uid} fcm {len(fcm)} device {device} RemDev {RemDevice}")
    if fcm == "remove": exeUnsubscribeFCM(uid)
    else: exeAddFcm(RemDevice, uid, fcm, device)
    return "success"



@app.get('/Single/{title}/{usid}', status_code=400)
async def sendSingleFCM(
    title:str, usid:str, res:Response,
    nbody:Annotated[str, Header()], popUp:str='no',
    cAction:Annotated[str, Header()] = default_cAction):

    body = nbody.replace('"','').replace("'","")
    print(f"START: aimUid {usid} body {body} cAct {cAction} popUp {popUp}")

    err, deviceToken = inputVali(cAction, usid)
    if err:
        print(err, " End")
        return err
    
    unrN = getUnr(usid)
    print(f"cAction {cAction} badge {unrN}, sending...")

    resp = sendfcmm(cAction, popUp, title, body, unrN, deviceToken, False)
    print('response: {0}, END'.format(resp))
    res.status_code = 200
    return "success"



@app.post('/Multi/{title}', status_code=400)
async def sendMultiFCM(title:str, req:Request, res:Response):
    folloUids = await req.json()
    print(f"START: Receivers {len(folloUids)} title {title}")
    fail, messages, i = (0,[],0)

    for data in folloUids:
        if i < 4: print(f"data {data}")
        err, deviceToken = inputVali(data['cAction'], data['uid'])
        if err:
            fail = fail + 1
            if i < 4: print(f"{err}, fail {fail}")
            i = i + 1
            continue
        unrN = getUnr(data['uid'])
        messages.append(
            sendfcmm(data['cAction'], "", title, data['body'], unrN, deviceToken, True)
        )
        i = i + 1

    if len(messages) < 1:
        print(f"messages empty, failed {fail}, End")
        return f"msg empty, failed {fail}"
    
    print(f"len of messages {len(messages)}, fails {fail}, sending...")
    resp = await sendMulti(messages)
    if not resp: return "send multi failed"
    
    print('{0} messages were sent successfully'.format(resp.success_count))
    res.status_code = 200
    return f"sent {resp.success_count} failed {fail}"


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)