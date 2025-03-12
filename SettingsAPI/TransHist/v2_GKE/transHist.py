from os import environ
from json import loads
from firebase_admin import firestore, auth, initialize_app

initialize_app()
db = firestore.client()

pfx = environ['DB_COLL_PREFIX']
qLim = int(environ['TRANS_QUERY_LIM'])
max_pagin = int(environ['TRANS_MAX_PAGIN'])
names = loads(environ['TRANSACTION_NAMES'])
ptyFromTemplate  = loads(environ['PRETTY_TX_ORIs'])

posiEvents = [*names['handWins'], names['others'][0]]
neutralEvents = [names['Special'][2], names['others'][2]]
negaEvents = [*names['handLosses'], names['others'][1]]


def iterateList(x, pageNeed, rows):
    arr = []
    hist = db.collection(f'{pfx}users/{x}/Transactions').order_by(
        u"date", direction=firestore.Query.DESCENDING).limit(qLim).get()
    
    L, sta = (len(hist), (pageNeed -1) *rows)
    sto = sta + rows -1
    print(f"start {sta} stop {sto} queryCount {L}")
    if L == 0: return False, L, arr
    if sto < sta: return "sta < sto", L, arr
    diff = L -sto -1
    if diff < 0: sto = sto + diff
    while sta <= sto:
        amount = False
        doc = hist[sta].to_dict()
        ptyFrom = ptyFromTemplate
        draw = f"0 {doc['currency']}"
        negative = f"-{doc['amount']} {doc['currency']}"
        positive = f"+{doc['amount']} {doc['currency']}"
        
        # determine + or - transaction:
        if doc['name'] == "transfer coins":
            if doc['from-id'] == x: amount = negative
            else: amount = positive
        if doc['name'] in negaEvents: amount = negative
        if doc['name'] in posiEvents: amount = positive
        if doc['name'] in neutralEvents: amount = draw
        if amount == False:
            sta = sta + 1
            print(f"error: transact {sta} amount not assigned, skip")
            continue
        if doc['from'] == "users":
            friend = auth.get_user(doc['from-id'])
            ptyFrom['users'] = friend.display_name
        try: polygonHash = doc['transHash']
        except: polygonHash = "NotFound"
        
        arr.append({
            "amount":amount,
            "date":doc['date'],
            "hash":polygonHash,
            "payer-id":doc['from-id'],
            "weje-transaction-id":hist[sta].id,
            "transaction name": doc['name'].capitalize(),
            "transaction origin": ptyFrom[doc['from']],
            "commission": f"{round(doc['fee'], 4)} {doc['currency']}"
        })
        sta = sta + 1
    return False, L, arr