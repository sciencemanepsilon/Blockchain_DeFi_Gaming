from requests import get
from os import environ
from elasticsearch import Elasticsearch
from google.oauth2.id_token import fetch_id_token
from google.auth.transport.requests import Request

auth_req = Request()
sysApi = environ["SYS_CONFIG_API"]
id_token = fetch_id_token(auth_req, sysApi)
print("tok for sys-config api call: ", len(id_token))

data = get(
    sysApi, params={"oriApi": "sessToBq"},
    headers={"Authorization": f"Bearer {id_token}"}
).json()

dataSet = data['dataSet']
tidSess = data['tidSess']
tidUsers = data['tidUsers']
proId = data['proId']
indexUsersWeje = data['indexUsersWeje']
schemaSess = data['schemaSess']
schemaUsersData = data['schemaUserData']

es = Elasticsearch(
    cloud_id=data['ELASTIC_CID'],
    api_key=(data['ELASTIC_APIKEY_ID'] ,data['ELASTIC_APIKEY_RAW'])
)
if es.ping(): print("ES connection True")
else: print("ES failed: ", es.info())

def testEs(index):
    resp = es.search(index=index, query={"match_all": {}},)
    print("Got %d Hits:" % resp['hits']['total']['value'])
    for hit in resp['hits']['hits']:
        print(hit["_source"])
    return 0

def addUserElastic(index, doc):
    try: elaRes = es.index(index=index, document=doc)
    except Exception as e:
        print(f"ES indexing failed: {e}")
        return "failed or already exists"
    return elaRes['result']