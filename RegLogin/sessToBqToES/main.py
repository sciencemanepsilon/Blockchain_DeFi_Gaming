from os import environ
from asyncio import gather, sleep
from datetime import datetime
from flask import Flask, request, jsonify
from BigQuery import writeBQ, schemaSessions, schemaUserData
from ElasticFunc import addUserElastic, indexUsersWeje, proId, dataSet, tidSess, tidUsers, testEs
app = Flask(__name__)

@app.route('/testES', methods=['GET'])
async def esTest():
    index = request.args.get('index')
    if index not in ["users", "sesscount", "users-weje"]:
        print("invalid index")
        return "invalid index", 200
    testEs(index)
    print("End")
    return "success", 200
     

@app.route('/forRegister', methods=['POST'])
async def EsNickBqSession():
    uid = request.json.get('uid')
    nick = request.json.get('nick')
    ip = request.json.get('ip')
    isMobile = request.json.get('isMobile')
    device = request.json.get('device')
    countryCode = request.json.get('countryCode')
    email = request.json.get('email')
    wid = request.json.get('wid')

    if None in [uid, device, nick, wid]:
        print("missing data")
        return jsonify({"error": "missing data"}), 200
    print(f"got {uid}, {ip}, isMobile {isMobile}, device: {device}")
    print("wallet id: ", wid)

    nickRes = addUserElastic(indexUsersWeje, {"nick":nick, "uid":uid})
    print("elastic nick write: ", nickRes)

    openDate = datetime.utcnow().replace(microsecond=0).timestamp()
    await gather(
        writeBQ("sessData", f"{proId}.{dataSet}.{tidSess}",[{
            "uid":uid, "ip":ip, "isMobile":isMobile,
            "openDate": openDate, "device": device
        }], schemaSessions),
        writeBQ("userData", f"{proId}.{dataSet}.{tidUsers}",[{
            "nickname": nick, "country": countryCode,
            "email":email, "register":openDate, "wid":wid,
            "deleted": None, "uid": uid, "isDeleted": False
        }], schemaUserData)
    )
    print("End")
    return jsonify({"nick":nickRes, "error":False}), 200


@app.route('/forLogin', methods=['POST'])
async def BqWriteOnLogin():
    uid = request.json.get('uid')
    ip = request.json.get('ip')
    isMobile = request.json.get('isMobile')
    device = request.json.get('device')

    if isMobile not in [True, False]:
        print("invalid is mobile: ", isMobile)
        return jsonify({"error":"invalid is mobile"}), 200
    print(f"got {uid}, {ip}, isMobile {isMobile}\n device: {device}")

    await writeBQ(
        "sessData",
        f"{proId}.{dataSet}.{tidSess}",
        [{
            "uid":uid, "ip":ip, "isMobile":isMobile,
            "openDate":datetime.utcnow().replace(microsecond=0).timestamp(),
            "device":device
        }],
        schemaSessions
    )
    print("End")
    return jsonify({"error":False}), 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))