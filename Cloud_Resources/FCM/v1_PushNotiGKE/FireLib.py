from os import environ
from asyncio import sleep
from firebase_admin import firestore, messaging, initialize_app
from google.cloud.firestore_v1.base_query import FieldFilter

initialize_app()
db = firestore.client()
pfx = environ['DB_COLL_PREFIX']
notiPicture = environ['FCM_LOGO']
BADGE_LIMIT = int(environ['FCM_BADGE_LIMIT'])
badStr = frozenset(["null", "undefined", "object Object", None])
print(f"env: pfx {pfx} logo {notiPicture} BadgeLim {BADGE_LIMIT}")


# Token Manage functions
def exeUnsubscribeFCM(uid):
    db.document(f"{pfx}users/{uid}").update({u"Session.fcm":None})
    return 0

def exeAddFcm(RemDevice, uid, fcm, deviceId):
    data = {
        u"Session.fcm": fcm,
        u"Session.device": deviceId,
        f"FcmDevices.{deviceId}": fcm
    }
    if RemDevice: data[f'FcmDevices.{RemDevice}'] = firestore.DELETE_FIELD
    db.document(f"{pfx}users/{uid}").update(data)
    return 0



# SEND FCM functions:
def inputVali(cAction, folloUids):
    if "https" not in cAction:
        return "missing https in click action",0
    if folloUids in badStr:
        return "missing usid",0

    doc = db.document(f"{pfx}users/{folloUids}").get().to_dict()
    if not doc: return "user doc not exist",0
    if "fcm" not in doc['Session']: return "fcm not found",0
    if doc['Session']['fcm'] in badStr: return "Session.fcm is null or bad",0
    if "-" in doc['Session']['status']: return "user in game",0
    return False, doc['Session']['fcm']


def getUnr(folloUids):
    unrN = db.collection(f"{pfx}messanger/{folloUids}/chats").where(
        filter=FieldFilter(u"isRead", u"==", False)).limit(BADGE_LIMIT).get()
    return len(unrN)


def sendfcmm(cAction, popUp, title, body, unrN, deviceToken, isMulti):
    msg = messaging.Message(
        data={
            "click_action":cAction,
            "popUpType":popUp,
            "title":title,
            "body":body,
            "badge":str(unrN),
            "image":notiPicture
        },
        token=deviceToken,
        #notification=messaging.Notification(title=title, body=body),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                icon=notiPicture, 
                title=title, 
                body=body, 
                badge=str(unrN), 
                vibrate=500
                ),
            fcm_options=messaging.WebpushFCMOptions(link=cAction)
        )
    )
    if isMulti: return msg
    try: return messaging.send(message=msg)
    except Exception as e:
        print(f"FCM error: {e}")
        return "internal FCM error"



async def sendMulti(messages):
    await sleep(0)
    try: response = messaging.send_each(messages)
    except Exception as e:
        print(f"send_each() failed: {e}, trying sendEach():")
        try: response = messaging.sendEach(messages)
        except Exception as e:
            print(f"sendEach() failed: {e}, trying sendEachAsync():")
            try: response = await messaging.sendEachAsync(messages)
            except Exception as e:
                print(f"sendEachAsync() failed: {e}, End")
                return False
    return response