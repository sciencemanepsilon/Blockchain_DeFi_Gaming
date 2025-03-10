from os import environ
from flask import Flask, request
from ElasticFunc import addUserElastic, changeNick
app = Flask(__name__)

@app.route('/forRegister', methods=['POST'])
def EsNickWrite():
    mesObj = request.json.get('message')
    att = mesObj['attributes']

    gMailRoute = att['GmailRoute']
    targetIndex = att['targetIndex']
    uid, nick = att['uid'], att['nick'] 
    print(f"START: {att}")

    if gMailRoute == "Yes":
        changeRes = changeNick(uid, nick, targetIndex)
        if not changeRes: return "fail", 500
        print("elastic nick change: ", changeRes, " End")
        return "done", 200
    if gMailRoute == "Non": return "done", 200

    nickRes = addUserElastic({"nick":nick, "uid":uid}, targetIndex )
    if not nickRes: return "fail", 500
    print("success elastic nick write: ", nickRes, ", End")
    return "done", 200


@app.route('/changeNick', methods=['POST'])
def EsNickChange():
    mesObj = request.json.get('message')
    attributes = mesObj['attributes']
    targetIndex = attributes['targetIndex']
    uid, nick = attributes['uid'], attributes['nick']
    if None in [uid, nick, targetIndex]:
        print("missing data, End")
        return "done", 200
    print(f"ChangeNick: got {uid}, nick {nick} index {targetIndex}")

    changeRes = changeNick(uid, nick, targetIndex)
    if not changeRes: return "fail", 500
    print("elastic nick change: ", changeRes, " End")
    return "Done", 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 8080)))