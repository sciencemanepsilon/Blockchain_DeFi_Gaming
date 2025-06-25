import json
from os import environ
from datetime import datetime
from google.cloud import pubsub_v1
from firebase_admin import initialize_app, firestore
# Listening to Leave-table-Topic triggered by finishHand and LeaveTable

PrettyGames = json.loads(environ['PRETTY_TX_ORIs'])
RevenueFactor = int(environ['REVENUE_PERCENT'])/100
project_id = environ['GOOGLE_CLOUD_PROJECT']
subscription_id = environ['LEAVE_TAB_TO_AFFILIATE_EARNINGS_SUB_ID']
timeoutt = int(environ['UPDATE_STATS_ListenTimeout'])


initialize_app()
db = firestore.client()
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)


def callback(message: pubsub_v1.subscriber.message.Message):
    ii = 0
    #ackid = message.ack_id
    data = json.loads(message.data.decode("utf-8"))
    if 'transHash' not in data:
        print(f"missing TxHash. {ii} Tx processed, END")
        return message.ack()
    
    txh = data['transHash']
    AffiArray = None
    if "affiliates" in data:
        AffiArray = data['affiliates']
    tid = message.attributes.get('tid')
    col = message.attributes.get('gameColl')
    mode = message.attributes.get('leaveMode')
    pfx = message.attributes.get('db_pfx')
    print(f"START: tid {tid} mode {mode} pfx {pfx} col {col} affi {AffiArray} txh {txh}")

    if not AffiArray:
        print(f"missing AffiArray. {ii} Tx processed, END")
        return message.ack()
    
    pretty = PrettyGames[col]
    dat = datetime.utcnow().replace(microsecond=0).isoformat() +'Z'
    if col == "BlackJack_Tables": comm = 1
    else:
        if not AffiArray[0]['TxVol']:
            print("Leave Table Poker/Ludo with no Tx, End")
            return message.ack()
        if 'poker' in col: comm = 0.01
        elif 'Ludo' in col: comm = 0.05
        else:
            print("invalid col, End")
            return message.ack()

    for ele in AffiArray:
        if not ele['TxVol']:
            print(f"missing TxVol for ele {ii+1}, next iteration")
            continue

        YourRev = ele['TxVol'] *comm *RevenueFactor
        OurRev = ele['TxVol'] *comm - YourRev
        AffiRef = db.document(f"{pfx}affiliates/{ele['Aid']}")
        PlayerRef = db.document(f"{pfx}users/{ele['Uid']}")

        tx = db.transaction()
        try:
            succ = UpdateAffiliateEarnings(
                tx, ele['Uid'], ele['TxVol'], YourRev,
                ele['Aid'], dat, pretty, txh, OurRev, AffiRef, PlayerRef, pfx
            )
            print(f"Tx success={succ}, tx {ii} complete")
        except Exception as e: print(f"Tx {ii} failed: {e}")
        ii += 1

    print(f"{ii} Tx processed, END")
    message.ack()


@firestore.transactional
def UpdateAffiliateEarnings(tx, uid, TxVol, YourRev, aid, dat, pretty, txh, OurRev, AffiRef, PlayerRef, pfx):
    print(f"TxStart pl {uid} {TxVol} POL AffiEarn {YourRev} aid {aid}")

    doc = AffiRef.get(transaction=tx)
    TotEarn = doc.get(u'TotalEarned') + YourRev
    unclm = doc.get(u'Unclaimed') + YourRev

    doc = PlayerRef.get(transaction=tx)
    earned = doc.get('affiliate.earned') + YourRev
    print(f"TotEarn {TotEarn} unclm {unclm} earned {earned}")

    tx.update(AffiRef, {u"TotalEarned":TotEarn, u"Unclaimed":unclm})
    tx.update(PlayerRef, {u"affiliate.earned":earned})
    tx.set(
        db.collection(f"{pfx}affiliateTx").document(), {
        u"Referent": uid,
        u"Affiliate": aid,
        u"Date": dat,
        u"Currency": u"POL",
        u"From": pretty,
        u"TxHash": txh,
        u"TxVolume": TxVol,
        u"OurRevenue": OurRev,
        u"YourRevenue": YourRev
    })
    return True


if __name__ == "__main__":
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=callback,
        await_callbacks_on_shutdown=True
    )
    print(f"Listening on {subscription_path}..Env timeout {timeoutt} AffiRevFactor {RevenueFactor}")

    with subscriber:
        try: streaming_pull_future.result(timeout=timeoutt)
        except Exception as e:
            print(f"subscriber stops Listener: {e}, End")
            streaming_pull_future.cancel()  # Trigger the shutdown.
            streaming_pull_future.result()  # Block until the shutdown is complete.