import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from json import dumps
from os import environ
from google.cloud import pubsub_v1
# called by: Login, Register, ChangeNickname

app = FastAPI()
dummyDict = {"key":"value"}
publisher = pubsub_v1.PublisherClient()
print("publisher client created")



@app.post('/', response_class=PlainTextResponse)
async def makePublish(request: Request):
    reqData = await request.json()
    topicPath = reqData['topicPath']
    jsonData = reqData['jsonData']
    attributes = reqData['attributes']
    if not attributes and not jsonData:
        return PlainTextResponse(content="no data", status_code=283)
    if not attributes: attributes = dummyDict
    if not jsonData: jsonData = dummyDict
    msg = dumps(jsonData)
    print("topicPath: "+ topicPath)

    err = callPubsub(topicPath, msg, attributes)
    if err:
        topicPath, err = newTopicPath(topicPath)
        if err: return PlainTextResponse(content=err, status_code=282)
        err = callPubsub(topicPath, msg, attributes)
        if err: return PlainTextResponse(content=err, status_code=281)
    return PlainTextResponse(content="success", status_code=200)



def newTopicPath(topicPath):
    if "/" not in topicPath: return False, "invalid tpath"
    arr = topicPath.split("/")
    pid, tid = (arr[1], arr[3])
    topicPath = publisher.topic_path(pid, tid)
    print("got new topicPath: "+ topicPath)
    return topicPath, False

def callPubsub(topicPath, msg, attributes):
    try:
        future = publisher.publish(topicPath, msg.encode("utf-8"), **attributes)
        print(f"pubsub call {future.result()}, SUCCESS, End")
    except Exception as e:
        print(f"pubsub call failed: {e}")
        return "pubsub call failed"
    return False

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT', 8080)))