from os import environ
from datetime import datetime
from json import loads
from connections import gmailChangeNick
from firebase_admin import firestore, initialize_app, auth
from google.oauth2 import id_token
from google.auth.transport import requests

class botUserRecord:
    def __init__(self, uid, nick, photo):
        self.uid = uid
        self.display_name = nick
        self.photo_url = photo

cPfx = environ['DB_COLL_PREFIX']
GmailoauthId = environ['ADD_EMAIL_CLIENT_ID']
baseStats = loads(environ['BASE_STATS'])
ChatWelcomeMsgText = environ['WELCOME_CHAT_MSG']
ChatWelcomeMsgButton = environ['WELCOME_CHAT_MSG_BUTTON']
if ChatWelcomeMsgButton == "": ChatWelcomeMsgButton = None
phoURL = environ['DIR_OF_PHOTO_URL']
buid = environ['BOT_UID']
bnick, bphoto = (environ['BOT_NICK'], environ['BOT_PHOTO'])
bot = botUserRecord(buid, bnick, bphoto)
custClaimsLabel = environ['CUSTOM_CLAIMS_ENV_LABEL']
print(f"prefix {cPfx}, chatButton {ChatWelcomeMsgButton}")
nickURL = "https://settings-nickname-svc:9011"

initialize_app()
db = firestore.client()
print("custom claims label: "+ custClaimsLabel)


def addEmailToFire(scookie, gmailToken):
    #if not verify_recaptcha(recaptcha_token)
    err, uid, wid = checkCookie(scookie)
    if err: return err,0,0,0,0

    err, email, gNick = checkGmail(gmailToken)
    if err: return err,0,0,0,0

    res = gmailChangeNick(
        nickURL + f'/PrivateCheckNick/UpdateElastic?nick={gNick}'
    )
    send_gNick = 0
    print("nickRes ", res.status_code)
    fireKwargs = {u"Email":email}
    authKwargs = {"email":email, "email_verified":True}

    if res.status_code == 200:
        rjson = res.json()
        if rjson['error'] == False:
            send_gNick = gNick
            fireKwargs = {**fireKwargs, u"nickname":gNick}
            authKwargs = {**authKwargs, "display_name":gNick}
        else: print(rjson['error'])

    try: auth.update_user(uid, **authKwargs)
    except: return "email already exists",0,0,0,0
    db.document(f'{cPfx}users/{uid}').update(fireKwargs)
    return False, uid, wid, email, send_gNick


def checkCookie(scookie):
    try: clm = auth.verify_session_cookie(scookie, check_revoked=True)
    except: return "invalid cookie",0,0

    uid = clm['uid']
    if custClaimsLabel != clm['platform']: return "platform mismatch",0,0

    if 'email_verified' not in clm:
        if 'email' not in clm:
            user = auth.get_user(uid)
            print(f"uid {uid} wid {clm['wid']} mailV {user.email_verified}")
            if user.email_verified: return "email already verified",0,0
        elif clm['email']: return "email already verified",0,0
    elif clm['email_verified']: return "email already verified",0,0
    print(f"cookie success, name {clm['name']} env {clm['platform']}")
    return False, uid, clm['wid']


def checkGmail(gmailToken):
    try: gmail = id_token.verify_oauth2_token(gmailToken, requests.Request(), GmailoauthId)
    except Exception as e:
        print(f"gmailTokenVeri failed: {e}")
        return "gmail verification failed",0,0
    
    print("gmail token info: ", gmail)
    email = gmail['email']
    if not gmail['email_verified']: return "gmail not verified",0,0
    if "@gmail.com" not in email or "+" in email: return "invalid gmail",0,0
    if gmail['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        return "invalid gmail",0,0
    if gmail['aud'] != GmailoauthId: return "invalid gmail",0,0
    return False, email, gmail['name'].replace(" ", "_")



def writeDB(email, nick, uid, countryCode, fmcToken, ip, device,
    isMobile, wid, widProvider):
    
    batch = db.batch()
    t = firestore.SERVER_TIMESTAMP
    baseData = {
        u'Session': {
            u'ip':ip, u'device':device, u'openDate':t,
            u'status':'online', u'isMobile':isMobile, u'sessCount':1
        },
        u'registerDate':t, u'wid':wid, u'Email':email,
        u'nickname':nick, u"countryCode":countryCode, u"walletProvider":widProvider,
        u'photoURI':phoURL + f"{countryCode}.png"
    }
    chatMsg = {
        u'from':bot.uid, u'body':ChatWelcomeMsgText,
        u'date':t, u'isRead':False, u'to':uid, u'button':ChatWelcomeMsgButton
    }
    #if fmcToken != "no":
        #arr = db.collection(u'FMC_Tokens').where(u'pushToken', u'==', fmcToken).get()
        #if len(arr) > 0:
            #batch.update(db.document(f'FMC_Tokens/{arr[0].id}'), {u'uid': uid})
            #print("fmc updated with uid")
        #else: print("fmc not found")
    #else: print("fmctoken=no was passed. Creating user without fmc token")

    batch.set(db.document(f'{cPfx}users/{uid}'), baseData)
    batch.set(db.document(f'{cPfx}baseStats/{uid}'), baseStats)
    batch.set(db.collection(f"{cPfx}users/{uid}/items").document(), {u"type":"friend-bot", u"id":bot.uid})
    batch.set(db.collection(f"{cPfx}messanger/{uid}/chats").document(), chatMsg)
    batch.commit()
    return 0

def setAuthObject(nick, countryCode, wid):
    try: user = auth.create_user(display_name=nick, photo_url=phoURL + f"{countryCode}.png")
    except Exception as e:
        print(f"auth.create user failed: {e}")
        return False, "Account creation failed"
    auth.set_custom_user_claims(user.uid, {
        'platform':custClaimsLabel, 'wid':wid
    })
    return user, False

def checkNickDB(nick):
    if len(db.collection(f'{cPfx}users').where(u'nickname', u'==', nick).get()) > 0:
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