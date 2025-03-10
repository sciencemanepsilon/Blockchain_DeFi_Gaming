from os import environ
from requests import get
from datetime import datetime
from flask import Flask, request, jsonify
from firebase_admin import firestore, auth, initialize_app
from config import genUserSnapsPerColl, initRoomLink, getPrettyAndRoomLink, getJWT
app = Flask(__name__)
res = get(
    environ['SYS_CONFIG_API'], params={"oriApi":"ShowGameTables"},
    headers={"Authorization":f"Bearer {getJWT(environ['SYS_CONFIG_API'])}"}
).json()

pubTabs = {}
initialize_app()
db = firestore.client()
print("sysConfig + firebase init done")
beta, liveDom, tc, max_pagin, maxTabAge = (
    res['beta'], res['live'],
    res['tableConfig'], res['maxPagin'], res['maxTabAge']
)
gamColls = genUserSnapsPerColl(tc)
print(f"gameColls {gamColls}, Server init done")


@app.route('/', methods=['GET'])
def showGameTables():
    ori = request.headers.get('ori')
    user = request.headers.get('uid')
    isPlayer = request.args.get('isPlayer')
    viewMore = request.args.get('isViewMore')
    game = request.args.get('game')

    err, domain = initRoomLink(
        beta, liveDom, ori,
        game, gamColls, isPlayer, viewMore
    )
    if err:
        print(domain)
        return jsonify({'error': domain}), 200
    print(f"got game {game} viewMore {viewMore} user {user}")

    if user in pubTabs:
        if viewMore == "no":
            if game in pubTabs[user]:
                tnow = datetime.utcnow().timestamp()
                if not pubTabs[user][game]['1stReq']:
                    pubTabs[user][game]['1stReq'] = datetime.utcnow().timestamp() -28
                diff = tnow - pubTabs[user][game]['1stReq']
                if diff < 10:
                    print("returning from cash")
                    return jsonify({
                        "error":"no error", "fromCash":True,
                        "gameArray":pubTabs[user][game]['arr']
                    }),200
                else: pubTabs[user][game]['arr'].clear()
            else: pubTabs[user][game] = {"1stReq":None, "arr":[]}
        else: pubTabs[user][game] = {"1stReq":None, "arr":[]}
    else: pubTabs[user] = {game: {"1stReq":None, "arr":[]}}
    
    arrF = iterateList(isPlayer, game, viewMore, user, domain)
    print(f"result: {len(arrF)}, user keys: {len(list(pubTabs.keys()))}, End")
    return jsonify({
        "error":"no error", "gameArray":arrF, "fromCash":False
    }), 200




def doQuery(isPl, coll, viewMore, game, uid):
    if viewMore == "no":
        if isPl == "yes":
            temp = db.collection(u"tables").where(
                u"game", u"==", coll).where(
                u"table.status", u"!=", "empty").limit(max_pagin).get()
            return temp
        temp = db.collection(u"tables").where(
            u"game", u"==", coll).where(
            u"table.status", u"!=", "empty").where(
            u"table.alloWatchers", u"==", True).limit(max_pagin).get()
        return temp
    #Else:
    try:
        snap = gamColls[game][coll][uid]
        print("snap found")
    except Exception as e:
        print(f"view more used, but its first query: {e}")
        return 0
    if snap in ["END", None]:
        print(f"snap is: {snap}")
        return snap
    if isPl == "yes":
        temp = db.collection(u"tables").where(
            u"games", u"==", coll).where(
            u"table.status", u"!=", "empty").start_after(snap).limit(max_pagin).get()
    else:
        temp = db.collection(u"tables").where(
            u"games", u"==", coll).where(
            u"table.status", u"!=", "empty").where(
            u"table.alloWatchers", u"==", True).start_after(snap).limit(max_pagin).get()
    if not isinstance(temp, list): return None
    return temp


def iterateList(isPl, game, viewMore, user, domain):
    doAgain = False
    if viewMore == "no":
        print("first query")
        for coll in gamColls[game]:
            temp = doQuery(isPl, coll, viewMore, game, user)
            if not temp:
                print("query is None")
                gamColls[game][coll][user] = "END"
                continue
            print(f"got len temp: {len(temp)}")
            doAgain = checkTemp(temp, coll, user, doAgain, game, domain)
            print(f"got doAgain: {doAgain}")
            if doAgain == 9:
                pubTabs[user][game]['1stReq'] = datetime.utcnow().timestamp()
                return pubTabs[user][game]['arr']
        if doAgain and len(pubTabs[user][game]['arr']) < max_pagin:
            print(f"rerunning with resArr: {len(pubTabs[user][game]['arr'])}")
            iterateList(isPl, game, "yes", user, domain)
            pubTabs[user][game]['1stReq'] = datetime.utcnow().timestamp()
        return pubTabs[user][game]['arr']
    # Else:
    print("view more query")
    for coll in gamColls[game].keys():
        temp = doQuery(isPl, coll, viewMore, game, user)
        if temp == 0: return iterateList(isPl, game, "no", user, domain)
        if temp == None:
            print("query or lastSnap is None")
            continue
        if temp == "END":
            print("view more not possible: reached END")
            continue
        print(f"in view more got temp: {len(temp)}")
        doAgain = checkTemp(temp, coll, user, doAgain, game, domain)
        if doAgain == 9: return pubTabs[user][game]['arr']
    if doAgain and len(pubTabs[user][game]['arr']) < max_pagin:
        iterateList(isPl, game, "yes", user, domain)
    return pubTabs[user][game]['arr']


def checkTemp(temp, coll, user, doAgain, game, domain):
    if len(temp) > 0:
        filtered = filterArr(temp, coll, domain)
        if len(filtered) > 0:
            pubTabs[user][game]['arr'].extend(filtered)
        if len(pubTabs[user][game]['arr']) >= max_pagin:
            gamColls[game][coll][user] = temp[-1]
            return 9
        if len(temp) == max_pagin and len(filtered) < max_pagin:
            doAgain = True
            print("doAgain set")
            gamColls[game][coll][user] = temp[-1]
    if len(temp) < max_pagin:
        print("query is exhausted")
        gamColls[game][coll][user] = "END"
    return doAgain


def filterArr(arr, coll, domain):
    res = []
    for tab in arr:
        pTab = tab.to_dict()
        tnow = datetime.utcnow().replace(microsecond=0).timestamp()
        try: topen = pTab['table']['openDate'].replace(microsecond=0).timestamp()
        except Exception as e:
            print("table timestamp failer: ", str(e))
            continue
        print("table age: ", tnow - topen)
        if tnow - topen < maxTabAge: continue
        if pTab['table']['public'] == False: continue
        if len(pTab['players']) < 1: continue
        if len(pTab['players']) >= pTab['table']['totalSeats']: continue
    
        #play = getPeople(pTab['players'], True)
        #if not play: continue
        #watch = getPeople(pTab['watchers'], False)
        try: admin = auth.get_user(pTab['table']['admin'])
        except:
            print("invalid admin")
            continue
        adm = {"name": admin.display_name, "photo": admin.photo_url}
        prettyLink = getPrettyAndRoomLink(0, coll, tc)
        res.append({
            "admin": adm,
            #"players": play,
            "players": [adm],
            #"watchers": watch,
            "watchers": [],
            "game": prettyLink[0],
            "media": pTab['table']['media'],
            "buyIn": pTab['table']['buyIn'],
            "currency": pTab['currency'],
            "minBet": pTab['table']['minBet'],
            "status": pTab['table']['status'],
            "link": domain + prettyLink[1] + tab.id +"&gameCollection=" + coll
        })
    print(f"got arr: {len(res)}")
    return res

def getPeople(arr, isPl):
    play = []
    for p in arr:
        try:
            pl = auth.get_user(p)
            play.append({"name": pl.display_name, "photo": pl.photo_url})
        except:
            if isPl: return []
            else: play.append({"name":"Not found", "photo":"Not found"})
    return play

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))