import uvicorn, os
from time import time
from datetime import datetime
from typing import Annotated
from fastapi import FastAPI, Header
from firebase_admin import firestore, initialize_app

StatsCash = {}
app = FastAPI()
initialize_app()
statCashExpire = 12
db = firestore.client()

@app.get('/')
async def makeGetDoc(ori:Annotated[str, Header()], uid:Annotated[str, Header()]):
    print(f"uid {uid} ori {ori}")
    if uid in StatsCash:
        if time() - StatsCash[uid]['age'] < statCashExpire:
            doc = StatsCash[uid]['doc']
            print("statsCash used")
        else:
            doc = fetchDoc("baseStats", uid)
            StatsCash[uid] = {"doc":doc, "age":time()}
            print("statsCash expired")
    else:
        doc = fetchDoc("baseStats", uid)
        StatsCash[uid] = {"doc":doc, "age":time()}
        print("user not in statsCash, cash set")
    
    docUsers = fetchDoc("users", uid)
    resUsers = {
        "countryCode": docUsers["countryCode"],
        "widProvider": docUsers["walletProvider"]
    }
    print(f"country {resUsers['countryCode']}")

    # Check inGame:
    inGame = False
    if "-" in docUsers['Session']['status']: inGame = True
    if inGame == True:
        print(f"in game: {inGame}, End")
        return {
            "error":"no error", "success":True, "userDoc":resUsers,
            "doc":doc, "inGame":inGame, "inQue":False, "lastQueDate":None,
            "datetimeNow":datetime.utcnow().isoformat() +"Z"
        }
    
    inQue = checkInQue(uid)
    if inQue == False:
        print(f"in Que: {inQue}, End")
        return {
            "error": "no error", "success": True, "userDoc": resUsers,
            "doc": doc, "inGame": inGame, "inQue": False, "lastQueDate":None,
            "datetimeNow": datetime.utcnow().isoformat() +"Z"
        }

    try: lastQue = docUsers['lastQueDate']
    except: lastQue = datetime.utcnow().replace(microsecond=0).isoformat() +"Z"
    print(f"last Que: {lastQue}, END")
    return {
        "error": "no error", "success": True, "userDoc": resUsers,
        "doc": doc, "inGame": inGame, "inQue": inQue, "lastQueDate": lastQue,
        "datetimeNow": datetime.utcnow().isoformat() +"Z"
    }


def fetchDoc(coll, uid):
    return db.document(f"{coll}/{uid}").get().to_dict()

def checkInQue(uid):
    return False

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))