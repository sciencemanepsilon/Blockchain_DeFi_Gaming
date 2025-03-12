import httpx, uvicorn
from os import environ
from firebase_admin import initialize_app, auth
from fastapi import FastAPI, Request
# called by connect-wallet, calling KAFKA pubsub-caller-svc
app = FastAPI()
hpx = httpx.Client(timeout=None)
topicPath = environ['LOGIN_TOPIC_PATH']
maxSessCount = int(environ['MAXSESS_COUNT'])
pubsubCallerApi = environ['PUBSUB_CALLER_SVC_NAME']
initialize_app()

@app.post('/')
async def signinWallet(request: Request):
    rData = await request.json()
    device, ip, isMobile, uid, sessCount, nick = (
        rData['device'], rData['ip'], rData['isMobile'],
        rData['uid'], rData['sessCount'], rData['nick']
    )
    print(
        f"nick {nick} device {device}\n",
        f"uid {uid}, sessCount {sessCount}, ipPassed {ip}"
    )
    try: id_token = auth.create_custom_token(uid)
    except Exception as e:
        print(f"custom token creation failed: {e}")
        return {'error':'crToken failed'}

    # to BigQuery SQL
    sess = None
    if sessCount != -9:
        erg = hpx.post(
            pubsubCallerApi, json={
            "topicPath":topicPath, "attributes":{"dummy":"value"},
            "jsonData":{"ip":ip,"device":device,"uid":uid,"isMobile":isMobile}
        })
        print(f"PubsubCaller Res: {erg.status_code} {erg.text}")
        
        if sessCount < maxSessCount:
            print("sessCount inced")
            sess = sessCount + 1
        if sessCount >= maxSessCount:
            print("sessCount field deleted")
            sess = "delete"
    
    print("End")
    return {'idtoken':id_token.decode("utf-8"), 'error':False, 'sessCount':sess}

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT', 8080)))