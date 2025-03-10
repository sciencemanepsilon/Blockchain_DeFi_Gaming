import httpx
from os import environ

hpx = httpx.Client(timeout=None)
esTargetIndex = environ['ES_INDEX_NAME']
GeoIpApi = environ['GEO_IP_API']
pubsubApi = environ['PUBSUB_CALLER_SVC_NAME']
topicPath = environ["REGISTER_TOPIC_PATH"]

def getGeo(ip):
    try: hits = hpx.get(GeoIpApi + ip).json()
    except Exception as e:
        print(f"geoApi call failed: {e}")
        return None
    if not hits:
        print("geoApi Res is null: ", hits)
        return None
    print(f"got {hits['country_name']} code: {hits['country_code']} city: {hits['city']}")
    return hits['country_code']

def EsIndexNickWriteSessBQ(uid, nick, ip, isMobile, device, countryCode, email, wid, gmail):
    return hpx.post(
        pubsubApi, json={
            "topicPath":topicPath,
            "attributes":{
                "uid":uid, "nick":nick,
                "targetIndex":esTargetIndex, "GmailRoute":gmail
            },
            "jsonData":{
                "uid":uid, "nick":nick, "wid":wid,
                "ip":ip, "isMobile":isMobile, "device":device,
                "countryCode":countryCode, "email":email
    }})

def gmailChangeNick(url):
    return hpx.get(url)