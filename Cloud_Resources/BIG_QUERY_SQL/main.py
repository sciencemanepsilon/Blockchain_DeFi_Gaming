import json
from base64 import b64decode
from os import environ
from datetime import datetime
from flask import Flask, request
from BigQuery import writeBQ, schemaSessions, schemaUserData, AddEmailToSQL
from ElasticFunc import proId, dataSet, tidSess, tidUsers
app = Flask(__name__)


@app.route('/forRegister', methods=['POST'])
def EsNickBqSession():
    mesObj = request.json.get('message')
    att = mesObj['attributes']
    gMailRoute = att['GmailRoute']
    jsonStrData = mesObj['data']
    jsonStrData = b64decode(jsonStrData).decode("utf-8").strip()
    data = json.loads(jsonStrData)

    if data['email']:
        AddEmailToSQL(
            data['uid'],
            f"{proId}.{dataSet}.{tidUsers}", data['email'],
            data['nick'], gMailRoute
        )
        return "done", 200
    
    uid, nick, ip, isMobile, device, countryCode, email, wid = (
        data['uid'],data['nick'], data['ip'],
        data['isMobile'], data['device'],
        data['countryCode'], data['email'], data['wid']
    )
    if None in [uid, device, nick, wid]:
        print("missing data")
        return "missing data", 200
    print(f"got {uid}, {ip}, isMobile {isMobile}\n device: {device}")
    print("wallet id: ", wid)

    openDate = datetime.utcnow().replace(microsecond=0).timestamp()
    writeBQ("sessData", f"{proId}.{dataSet}.{tidSess}",[{
        "uid":uid, "ip":ip, "isMobile":isMobile,
        "openDate": openDate, "device": device
    }], schemaSessions)

    writeBQ("userData", f"{proId}.{dataSet}.{tidUsers}",[{
        "nickname": nick, "country": countryCode,
        "email":email, "register":openDate, "wid":wid,
        "deleted": None, "uid": uid, "isDeleted": False
    }], schemaUserData)
    print("End")
    return "done", 200


@app.route('/forLogin', methods=['POST'])
def BqWriteOnLogin():
    mesObj = request.json.get('message')
    #attributes = mesObj['attributes']
    jsonStrData =mesObj['data']
    jsonStrData = b64decode(jsonStrData).decode("utf-8").strip()
    data = json.loads(jsonStrData)

    uid, ip, isMobile, device = (
        data['uid'], data['ip'], data['isMobile'], data['device']
    )
    if isMobile not in [True, False]:
        print("invalid is mobile: ", isMobile)
        return "invalid is mobile", 200
    print(f"got {uid}, {ip}, isMobile {isMobile}\n device: {device}")

    writeBQ(
        "sessData",
        f"{proId}.{dataSet}.{tidSess}",
        [{
            "uid":uid, "ip":ip, "isMobile":isMobile,
            "openDate":datetime.utcnow().replace(microsecond=0).timestamp(),
            "device":device
        }], schemaSessions
    )
    print("End")
    return "done", 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(environ.get('PORT', 8080)))