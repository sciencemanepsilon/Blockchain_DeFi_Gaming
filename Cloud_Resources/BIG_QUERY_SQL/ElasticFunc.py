from requests import get
from os import environ
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
schemaSess = data['schemaSess']
schemaUsersData = data['schemaUserData']