from os import environ
from flask import Flask, request, jsonify
from connections import EsIndexNickWriteSessBQ, getGeo
from firebase import checkNickDB, setAuthObject, writeDB, custTok
app = Flask(__name__)

@app.route('/', methods=['POST'])
def register():
    ipList = request.access_route
    ipReal = request.access_route[0]
    ipAdd = request.headers.get('ip')
    device = request.headers.get('device')
    fmcToken = request.headers.get('fmctoken')
    wid = request.json.get('wid')
    widProvider = request.json.get('widProvider')
    email = request.json.get('email')
    isMobile = request.json.get('isMobile')
    nick = request.json.get('nick')
    countryCode = request.json.get('countryCode')
    print(f"firstIP {ipReal} from {ipList}")
    print(f"got nick {nick} ip {ipAdd} country {countryCode} wid {widProvider}")

    nickRes = checkNickDB(nick)
    if nickRes:
        print(nickRes)
        return jsonify({"error":nickRes}), 200
    if not countryCode: countryCode = getGeo(ipAdd)

    # Create Auth Object
    user, errMsg = setAuthObject(nick, countryCode)
    if errMsg: return jsonify({"error":errMsg}), 200
    if not user:
        print("user record failed")
        return jsonify({"error":"User record creation failed"}), 200

    erg = EsIndexNickWriteSessBQ(
        user.uid, nick, ipAdd,
        isMobile, device, countryCode, email, wid
    )
    print(f"PubsubCaller Res: {erg.status_code} {erg.text}")
    
    id_token = custTok(user.uid)
    if len(id_token) < 30:
        print("End")
        return jsonify({'error': 'token FB api failed'}), 200

    writeDB(
        email, nick, user.uid, countryCode, fmcToken,
        ipAdd, device, isMobile, wid, widProvider
    )
    print("token success, DB wrote, End")
    return jsonify({"error":False, "idtoken":id_token, "uid":user.uid}), 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))