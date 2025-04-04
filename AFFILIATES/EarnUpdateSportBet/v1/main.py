import json
from os import environ
from datetime import datetime
from google.cloud import pubsub_v1
from firebase_admin import initialize_app, firestore
# Listening to UPDATE_AFFILIATE_EARN_SPORT_BET_TOPIC_PATH triggered by SportBetApi

comm = 0.05
pretty = "Sport Bet"
pfx = environ['DB_COLL_PREFIX']
RevenueFactor = int(environ['REVENUE_PERCENT'])/100
project_id = environ['GOOGLE_CLOUD_PROJECT']
subscription_id = environ['SPORT_BET_TO_AFFILIATE_EARNINGS_SUB_ID']
timeoutt = int(environ['UPDATE_STATS_ListenTimeout'])
print(f"subId {subscription_id} pfx {pfx} timeout {timeoutt} comm {comm}")

initialize_app()
db = firestore.client()
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)


def callback(message: pubsub_v1.subscriber.message.Message):
    ackid = message.ack_id
    data = json.loads(message.data.decode("utf-8"))
    print(f"START: {data} ackid {ackid}")
    if 'TxHash' not in data or 'TxVol' not in data or 'BetId' not in data or 'currency' not in data or 'ArrayItem' not in data:
        print("missing key in json, End")
        return message.ack()
    
    txh = data['TxHash']
    TxVol = data['TxVol']
    BetId = data['BetId']
    currency = data['currency']
    ele = data['ArrayItem']
    dat = datetime.utcnow().replace(microsecond=0).isoformat() +'Z'
    if 'Aid' not in ele or 'Uid' not in ele:
        print("missing Aid, End")
        return message.ack()

    YourRev = TxVol *comm *RevenueFactor
    OurRev = TxVol *comm - YourRev
    AffiRef = db.document(f"{pfx}affiliates/{ele['Aid']}")
    PlayerRef = db.document(f"{pfx}users/{ele['Uid']}")

    tx = db.transaction()
    try:
        succ = UpdateAffiliateEarnings(
            tx, ele['Uid'], TxVol, YourRev,
            ele['Aid'], dat, txh, OurRev, AffiRef, PlayerRef,
        )
        print(f"Tx success {succ}, END")
        message.ack()
    except Exception as e:
        print(f"Tx failed: {e}, End")
        message.nack()


@firestore.transactional
def UpdateAffiliateEarnings(tx, uid, TxVol, YourRev, aid, dat, txh, OurRev, AffiRef, PlayerRef):
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
    print(f"Listening for messages on {subscription_path}..\n")

    with subscriber:
        try: streaming_pull_future.result(timeout=timeoutt)
        except Exception as e:
            print(f"subscriber stops Listener, err: {e}")
            streaming_pull_future.cancel()  # Trigger the shutdown.
            streaming_pull_future.result()  # Block until the shutdown is complete.

    print("subscriber Listener closed, container terminate, End")