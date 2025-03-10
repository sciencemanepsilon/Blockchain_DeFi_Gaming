from time import time
from datetime import datetime
from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request
tokCash = {
    "Login": {"age":0, "tok":None},
    "Register": {"age":0, "tok":None}
}
switchDeviceMinutesTreshold = 0.5

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
        if diff < 3400:
            print("rejecting re-login, End")
            return 1, "user logged in with same device"
        return 2, "ReLogin with same device"
    
    print("switch device case, since last login minutes: ", round(diff/60,1))
    if diff < 60 * switchDeviceMinutesTreshold:
        return 3, "frequent device switch forbidden"
    return 2, "Relogin switching device"


def getJWT(audience):
    auth_req = Request()
    jwt = fetch_id_token(auth_req, audience)
    print(f"tok for {audience}: {len(jwt)}")
    return jwt

def setCashAndGetTok(apiName, api):
    tok = getJWT(api)
    tokCash[apiName]['tok'] = tok
    tokCash[apiName]['age'] = time()
    return tok

def checkJwtCash(apiName, url):
    if not tokCash[apiName]['tok']: return setCashAndGetTok(apiName, url)
    if time() -tokCash[apiName]['age'] > 3400: return setCashAndGetTok(apiName, url)
    return tokCash[apiName]['tok']


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