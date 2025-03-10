import requests
from time import time
from firebase import GeoIpApi, getJWT
from firebase import pubsubApi, tokCash, topicPath

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
    if time() -tokCash['age'] > 56 *60: idtok = setCashAndGetTok(pubsubApi)
    else: idtok = tokCash['tok']
    return requests.post(
        pubsubApi, json={
            "topicPath":topicPath,
            "attributes":{"uid":uid, "nick":nick},
            "jsonData":{
                "uid":uid, "nick":nick, "wid":wid,
                "ip":ip, "isMobile":isMobile, "device":device,
                "countryCode":countryCode, "email":email
        }},
        headers={"Authorization":f"Bearer {idtok}"}
    )
