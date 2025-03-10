import httpx, time
from os import environ
from datetime import datetime
from firebase_admin import firestore, initialize_app
from google.cloud.firestore_v1.base_query import FieldFilter

initialize_app()
db = firestore.client()
hpx = httpx.Client(timeout=None)
pfx = environ['DB_COLL_PREFIX']
switchDeviceMinutesTreshold = float(environ['SWITCH_DEVICE_MINUTES_TRESH'])
sameDeviceLoginSecondsTreshold = int(environ['SAME_DEVICE_SECONDS_TRESH'])
idtokenFreshness = int(environ['ID_TOKEN_FRESHNESS'])
customClaimsEnvLabel = environ['CUSTOM_CLAIMS_ENV_LABEL']
authOpsApi = environ['AUTH_OPS_API']
authApiRoute = environ['tryBothTokensRoute']
FCM_DEVICE_MAX_COUNT = int(environ['FCM_DEVICE_MAX_COUNT'])
print(f"idTokFresh {idtokenFreshness} custClaimsLabel {customClaimsEnvLabel}")
print(f"swDevTresh {switchDeviceMinutesTreshold} samDevTresh {sameDeviceLoginSecondsTreshold}")


def writeEmailBonusTx(uid, amount, hhash):
    ref = db.collection(f'{pfx}users/{uid}/Transactions').document()
    ref.set({
        u"name":"Reward", u"from":"Gmail",
        u"from-id":ref.id, u"to":uid, u"date":datetime.utcnow().isoformat() +"Z",
        u"amount":amount, u"fee":0, u"currency":"POL", u"transHash":hhash
    })
    return 0


def isDocumentExist(collPath, fieldKey, fieldValue, op, reqUid):
    hits = db.collection(pfx + collPath).where(
        filter=FieldFilter(fieldKey, op, fieldValue)).limit(3).get()
    
    erg = False
    print(f"{fieldKey} == {fieldValue} was found {len(hits)} times")
    if not hits: return False
    for hit in hits:
        if hit.id != reqUid: erg = True
        doc = hit.to_dict()
        print(f"doc.id {hit.id}: {doc}")
    return erg


def queryWallHits(coll, wid):
    return db.collection(pfx + coll).where(filter=FieldFilter(u"wid",u"==",wid)).get()

def getBaseStats(uid):
    return db.document(f"{pfx}baseStats/{uid}").get().to_dict()

def isIdTokFresh(auth_time):
    diff = round(time.time() -auth_time, 2)
    print(f"id tok age: {diff} sec")
    return diff > idtokenFreshness

def getDeviceCase(newDevice):
    if newDevice: return "switch device"
    return "same device"

def getCTypeAndMsg(msg2):
    if not msg2: return "cookie", "cookie verification success"
    return "idtoken", "call the cookie-setter-api"

def parseCred(uid, newDevice, scookie, idtoken, userDoc):
    erg = hpx.get(authOpsApi +authApiRoute, headers={"scookie":scookie, "idtoken":idtoken})
    newDevCase = getDeviceCase(newDevice)
    if erg.status_code == 280:
        erg = erg.json()
        print(erg['msg1'] +", idTokMsg: "+ erg['msg2'])
        print(f"logged {newDevCase}, veri Auth-Token failed, making new login")
        return False
    if erg.status_code == 200:
        erg, msg = erg.json(), "Production Auth-Token Forbidden in Beta-Env"
        if erg['claimsEnv'] != customClaimsEnvLabel:
            return {"error":msg, "idtoken":None, "goProfile":False}

        ctype, msg = getCTypeAndMsg(erg['msg2'])
        if erg['uid'] == uid:
            print(f"logged {newDevCase}, {ctype} uid {erg['uid']} == wid-uid, End")
            if ctype == "idtoken":
                if not isIdTokFresh(erg['auth_time']):
                    return {
                        "error":"no error", "idtoken":None, "goProfile":True,
                        "msg":"refresh idtoken, set local storage, and call CookieSetter"
                    }
            if newDevice: return FcmLogics(uid, newDevice, userDoc, msg)
            return {
                "error":"no error", "idtoken":None, "goProfile":True,
                "msg":msg, "TriggerFcmPopup":False, "OverrideFcmDevice":False
            }
        
        print(f"logged {newDevCase}, {ctype} uid {erg['uid']} != wid-uid, End")
        return {
            "error":"Auth-Token and wallet id mismatch", "idtoken":None,
            "solution1":"Logout or clear browser data to use this wallet",
            "solution2":"Select the wallet you used last time", "goProfile":False
        }



def FcmLogics(uid, newDevice, userDoc, msg):
    fireData = {u"Session.device":newDevice}
    resData = {
        "error":"no error", "idtoken":None, "goProfile":True,
        "msg":msg, "TriggerFcmPopup":False, "OverrideFcmDevice":False
    }
    if "FcmDevices" in userDoc:
        if newDevice in userDoc['FcmDevices']:
            if userDoc['Session']['fcm'] != None:
                fireData[u'Session.fcm'] = userDoc['FcmDevices'][newDevice]
        elif len(userDoc['FcmDevices']) < FCM_DEVICE_MAX_COUNT:
            resData['TriggerFcmPopup'] = True
        else:
            resData['TriggerFcmPopup'] = True
            resData['OverrideFcmDevice'] = list(userDoc['FcmDevices'])[-1]
    else:
        resData['TriggerFcmPopup'] = True
    db.document(f"{pfx}users/{uid}").update(fireData)
    print(f"TriggerFcmPopup {resData['TriggerFcmPopup']} OverrideFcmDevice {resData['OverrideFcmDevice']}")
    return resData


def SameDeviceFcmLogics(ip, device, isMobile, sessCount, res, userDict, uid):
    sess = {
        u'Session.ip':ip, u'Session.device':device,
        u'Session.openDate':firestore.SERVER_TIMESTAMP,
        u'Session.status':'online', u'Session.isMobile':isMobile
    }
    if sessCount != -9:
        if res['sessCount'] == "delete":
            sess[u"Session.sessCount"] = firestore.DELETE_FIELD
        else:
            sess[u"Session.sessCount"] = res['sessCount']
    resData = {
        "error":"no error", "idtoken":res['idtoken'], "goProfile":True,
        "msg":"login success", "TriggerFcmPopup":False, "OverrideFcmDevice":False
    }
    if userDict['Session']['device'] != device:
        if "FcmDevices" in userDict:
            if device in userDict['FcmDevices']:
                if userDict['Session']['fcm'] != None:
                    sess[u'Session.fcm'] = userDict['FcmDevices'][device]
            elif len(userDict['FcmDevices']) < FCM_DEVICE_MAX_COUNT:
                resData['TriggerFcmPopup'] = True
            else:
                resData['TriggerFcmPopup'] = True
                resData['OverrideFcmDevice'] = list(userDict['FcmDevices'])[-1]
        else:
            resData['TriggerFcmPopup'] = True
    elif "fcm" in userDict['Session']:
        if userDict['Session']['fcm'] != None:
            if device in userDict['FcmDevices']:
                if userDict['FcmDevices'][device] != userDict['Session']['fcm']:
                    print("LoginSameDevice, FcmDevices.deviceId != Session.fcm, setting it")
                    sess[u'Session.fcm'] = userDict['FcmDevices'][device]
            elif len(userDict['FcmDevices']) < FCM_DEVICE_MAX_COUNT:
                print(f"device {device} is missing in FcmDevices, adding it")
                sess[f'FcmDevices.{device}'] = userDict['Session']['fcm']
            else:
                print(f"device {device} is missing in FcmDevices, overriding other")
                RemDevice = list(userDict['FcmDevices'])[-1]
                sess[f'FcmDevices.{device}'] = userDict['Session']['fcm']
                sess[f'FcmDevices.{RemDevice}'] = firestore.DELETE_FIELD
    else:
        resData['TriggerFcmPopup'] = True
        print("LoginSameDevice, Session.fcm not exist, ask user to subscribe")
    
    db.document(f"{pfx}users/{uid}").update(sess)
    print(f"TriggerFcmPopup {resData['TriggerFcmPopup']} OverrideFcmDevice {resData['OverrideFcmDevice']}")
    return resData



def convertOpenDate(oDate):
    return oDate.replace(microsecond=0).timestamp()

def checkDevice(sessDict, ip, device, nick):
    # 1: goProfile noLogin, 2: goProfile + ReLogin, 3: noGo noLogin
    print("found user online session")
    if sessDict['ip'] == ip: print("with same ip")
    else: print("with other ip")
    tnow = datetime.utcnow().replace(microsecond=0).timestamp()
    diff = tnow - sessDict['openDate'].replace(microsecond=0).timestamp()
    if sessDict['device'] == device:
        print(f"{nick} logged in with same device since {round(diff/60,1)} minutes")
        if diff < sameDeviceLoginSecondsTreshold:
            print("rejecting re-login, End")
            return 1, "user logged in with same device"
        return 2, "ReLogin with same device"
    
    print("switch device case, since last login minutes: ", round(diff/60,1))
    if diff < 60 * switchDeviceMinutesTreshold:
        return 3, "frequent device switch forbidden"
    return 2, "Relogin switching device"

def parseIPs(ipAdd, ipReal):
    reject = False
    if ipAdd in [None, "undefined", "0.0.0.0", ""]:
        print("missing ip, ipReal: ", ipReal)
        if not ipReal or ipReal == "0.0.0.0": reject = "ip fetch failed"
        elif "." not in ipReal and ":" not in ipReal: reject = "invalid ip"
        elif not validIpAddress(ipReal): reject = "invalid suspect ip"
        else:
            ipAdd = ipReal
            print("missing ip, but got real ip: ", ipReal)
    elif ipReal in ["", None, "0.0.0.0"]: print(f"got ip {ipAdd}, but ipReal is {ipReal}")
    elif ipAdd != ipReal:
        if "." not in ipReal and ":" not in ipReal: print("missing dot/colon in ipReal, taking geoIp")
        elif not validIpAddress(ipReal): print("suspect ipReal, taking geoIp")
        else:
            print(f"ip {ipAdd} != ipReal {ipReal}, setting ip=ipReal")
            ipAdd = ipReal
    else: print(f"good case. ip {ipAdd} == ipReal {ipReal}")
    return reject, ipAdd

def validIpAddress(ip):
    if "." in ip and ":" in ip: return False
    if "." in ip:
        ipArr = ip.split(".")
        for ele in ipArr:
            if not ele.isnumeric(): return False
            else:
                num = int(ele)
                if num < 0 or num > 255: return False
        return True
    if ":" in ip:
        ipArr = ip.split(":")
        for ele in ipArr:
            if ele in ["", None]: continue
            try: int(ele, 16)
            except:
                print("IPv6 HEX check failed")
                return False
        return True
    print("neither . nor : was found in IP")
    return False

def callRegLoginApi(url, head, myJson):
    return hpx.post(url, headers=head, json=myJson)