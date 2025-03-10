from os import environ
from elasticsearch import Elasticsearch

es = Elasticsearch(
    cloud_id=environ['ELASTIC_CID'],
    api_key=(environ['ELASTIC_APIKEY_ID'] ,environ['ELASTIC_APIKEY_RAW'])
)
if es.ping(): print("ES connection: ", es.ping())
else: print("ES failed: ", es.info())


def addUserElastic(doc, targetIndex):
    try: elaRes = es.index(index=targetIndex, document=doc)
    except Exception as e:
        print(f"ES nickWrite (indexing) failed: {e}\nEnd")
        return False
    return elaRes['result']


def changeNick(uid, nick, targetIndex):
    res = es.search(
        index=targetIndex,
        query={"query_string": {"query":uid, "fields":["uid"]}}
    )
    if res['hits']['total']['value'] > 0:
        esId = res['hits']['hits'][0]['_id']
        try:
            resp = es.update(index=targetIndex, id=esId, doc={"nick":nick, "uid":uid})
            return resp['result']
        except:
            print("nick elastic.update failed, esId: ", esId, "\nEnd")
            return False
    print("uid notFound in Elastic: ", res['hits']['total']['value'], "\nEnd")
    return False