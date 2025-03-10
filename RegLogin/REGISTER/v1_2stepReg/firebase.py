import requests
from os import environ
from firebase_admin import firestore, initialize_app, auth
from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request

class botUserRecord:
    def __init__(self, uid, nick, photo):
        self.uid = uid
        self.display_name = nick
        self.photo_url = photo

def getJWT(audience):
    auth_req = Request()
    jwt = fetch_id_token(auth_req, audience)
    print(f"tok for {audience}: {len(jwt)}")
    return jwt

data = requests.get(
    environ['SYS_CONFIG_API'], params={"oriApi":"Register"},
    headers={"Authorization":f"Bearer {getJWT(environ['SYS_CONFIG_API'])}"}
).json()

initialize_app()
db = firestore.client()
EsBqApi = data['EsBqApi']
GeoIpApi = data['GeoIpApi']
baseStats = data['baseStats']
ChatWelcomeMsgText = data['ChatWelcomeMsgText']
ChatWelcomeMsgButton = data['ChatWelcomeMsgButton']
gsPhoUri = data['gs-default-avatar']
phoURL = data['default-avatar']
bot = botUserRecord(data['botUid'], data['botNick'], data['botPhoto'])


def writeDB(email, nick, uid, countryCode, fmcToken, ip, device, isMobile, wid, widProvider):
    batch = db.batch()
    t = firestore.SERVER_TIMESTAMP
    baseData = {
        u'Session': {
            u'ip':ip, u'device':device, u'openDate':t,
            u'status':'online', u'isMobile':isMobile, u'sessCount':1
        },
        u'photoURI':gsPhoUri, u'registerDate':t,
        u'wid':wid, u'Email':email, u'nickname':nick,
        u"countryCode":countryCode, u"walletProvider":widProvider
    }
    chatMsg = {
        u'from': {u'name':bot.display_name, u'uid':bot.uid},
        u'body':ChatWelcomeMsgText, u'date':t, u'isRead':False,
        u'to':uid, u'photoURL':bot.photo_url, u'button':ChatWelcomeMsgButton
    }
    #if fmcToken != "no":
        #arr = db.collection(u'FMC_Tokens').where(u'pushToken', u'==', fmcToken).get()
        #if len(arr) > 0:
            #batch.update(db.document(f'FMC_Tokens/{arr[0].id}'), {u'uid': uid})
            #print("fmc updated with uid")
        #else: print("fmc not found")
    #else: print("fmctoken=no was passed. Creating user without fmc token")

    batch.set(db.document(f'users/{uid}'), baseData)
    batch.set(db.document(f'baseStats/{uid}'), baseStats)
    batch.set(db.collection(f"users/{uid}/items").document(), {u"type":"friend-bot", u"id":bot.uid})
    batch.set(db.collection(u"messanger").document(uid), {u"nickname": nick})
    batch.set(db.collection(f"messanger/{uid}/chats").document(), chatMsg)
    batch.commit()
    return 0

def setAuthObject(nick):
    try: user = auth.create_user(display_name=nick, photo_url=phoURL)
    except Exception as e:
        print(f"auth.create user failed: {e}")
        return False, "Account creation failed"
    auth.set_custom_user_claims(user.uid, {'platform':'live'})
    return user, False

def checkNickDB(nick):
    if len(db.collection(u'users').where(u'nickname', u'==', nick).get()) > 0:
        print("nick exist in DB")
        return 'nick exists'
    
    print(f"checks passed, nick {nick} is not in DB")
    return False

def custTok(uid):
    try: id_token = auth.create_custom_token(uid)
    except Exception as e:
        print(f"custom token creation failed: {e}")
        return 'token FB api failed'
    return id_token.decode("utf-8")