import requests
from time import time
from firebase import EsBqApi, GeoIpApi, getJWT
tokCash = {"age":0, "tok":None}

def setCashAndGetTok(api):
    tok = getJWT(api)
    tokCash['tok'] = tok
    tokCash['age'] = time()
    return tok

def getGeo(ip):
    try: hits = requests.get(GeoIpApi + ip).json()
    except Exception as e:
        print(f"geoApi call failed: {e}")
        return None
    if not hits:
        print("geoApi Res is null: ", hits)
        return None
    print(f"got {hits['country_name']} code: {hits['country_code']} city: {hits['city']}")
    return hits['country_code']


def EsIndexNickWriteSessBQ(uid, nick, ip, isMobile, device, countryCode, email, wid):
    if not tokCash['tok']: idtok = setCashAndGetTok(EsBqApi)
    elif time() -tokCash['age'] > 3400: idtok = setCashAndGetTok(EsBqApi)
    else: idtok = tokCash['tok']
    
    erg = requests.post(
        EsBqApi + "/forRegister",
        json={
            "uid":uid, "nick":nick, "wid":wid,
            "ip":ip, "isMobile":isMobile, "device":device,
            "countryCode":countryCode, "email":email
        },
        headers={"Authorization":f"Bearer {idtok}"},
    ).json()
    print("EsIndexNickWriteSessBQ res: ", erg)
    return erg
