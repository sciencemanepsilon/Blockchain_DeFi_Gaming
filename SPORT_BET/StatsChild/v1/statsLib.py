from os import environ
from math import sqrt
from datetime import datetime
from firebase_admin import initialize_app, firestore

initialize_app()
db = firestore.client()
pfx = environ['DB_COLL_PREFIX']

def initTx(uid, action, amount, betId, fee, txHash, txId):
    tx = db.transaction()
    return txRun(tx, uid, action, amount, betId, fee, txHash, txId)

def setTotals(totKey, action, amount, dat, snap):
    totWin = snap.get(f'{totKey}.win')
    totLose = snap.get(f'{totKey}.lose')
    if action == 'win':
        totWinLose = totWin + 1
        neWL = calcWL(totWinLose, totLose)
    else:
        totWinLose = totLose + 1
        neWL = calcWL(totWin, totWinLose)
    return neWL, {
        **dat,
        f'{totKey}.wl_ratio': neWL,
        f'{totKey}.{action}': totWinLose,
        f'{totKey}.games': snap.get(f'{totKey}.games') + 1,
        f'{totKey}.{action}Coins': snap.get(f'{totKey}.{action}Coins') + amount
    }

@firestore.transactional
def txRun(tx, uid, action, amount, betId, fee, txHash, txId):
    print(f"START tx: user {uid} {action} {amount} POL fee {fee} betID {betId} txId {txId}")
    oldDocSnap = db.document(f"{pfx}baseStats/{uid}").get(transaction=tx)
    neWL, dat = setTotals("total", action, amount, {}, oldDocSnap)
    # Max
    if neWL > oldDocSnap.get(u'max.wl_ratio'): dat[u'max.wl_ratio'] = neWL
    if amount > oldDocSnap.get(f'max.{action}Coins'): dat[f'max.{action}Coins'] = amount
    
    if 'SPORT_BET' in oldDocSnap.to_dict():
        neWL, dat = setTotals("SPORT_BET", action, amount, dat, oldDocSnap)
        # Max
        if neWL > oldDocSnap.get(u'SPORT_BET.max.wl_ratio'):
            dat[u'SPORT_BET.max.wl_ratio'] = neWL
        if amount > oldDocSnap.get(f'SPORT_BET.max.{action}'):
            dat[f'SPORT_BET.max.{action}'] = amount
    else:
        if action == 'win': SpWin, SpMaxWin, SpLose, SpMaxLose = (1,amount,0,0)
        else: SpWin, SpMaxWin, SpLose, SpMaxLose = (0,0,1,amount)
        WL = calcWL(SpWin, SpLose)
        dat = {
            **dat,
            u'SPORT_BET.games': 1,
            u'SPORT_BET.win': SpWin,
            u'SPORT_BET.lose': SpLose,
            u'SPORT_BET.wl_ratio': WL,
            u'SPORT_BET.winCoins': SpMaxWin,
            u'SPORT_BET.loseCoins': SpMaxLose,
            u'SPORT_BET.max': {u'win':SpMaxWin, u'lose':SpMaxLose, u'wl_ratio':WL}
        }
    tx.update(db.document(f"{pfx}baseStats/{uid}"), dat)
    txRef = db.collection(f"{pfx}users/{uid}/Transactions")
    if txId: txRef = txRef.document(txId)
    else: txRef = txRef.document()
    tx.set(
        txRef, {
        u'to': uid,
        u'name': f'game {action}',
        u'from': u'sport bets',
        u'from-id': betId,
        u'date': datetime.utcnow().replace(microsecond=0).isoformat() +'Z',
        u'amount': amount,
        u'fee': fee,
        u'currency': u'POL',
        u'transHash': txHash
    })
    return "success"


def calcWL(win, lose):
    if win == 0: return 0
    if lose == 0: return round(0.03 * win*win + 1, 2)
    if lose == 1: return round(0.02 * win*win + 1, 2)
    if lose == 2: return round(0.7 * sqrt(win) - 0.11, 2)
    if lose == 3: return round(0.81* sqrt(win) -0.477, 2)
    return round(win/lose,2)