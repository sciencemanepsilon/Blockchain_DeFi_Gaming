import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from json import dumps
from os import environ
from concurrent import futures
from google.cloud import pubsub_v1
# '/' called by: Login, Register, ChangeNickname

app = FastAPI()
dummyDict = {"key":"value"}
publisher = pubsub_v1.PublisherClient()
maxmsg = int(environ['PUBSUB_BATCH_MSG_SIZE_TRESHOLD'])
maxbytes = int(environ['PUBSUB_BATCH_BYTES_TRESHOLD'])
maxtime = int(environ['PUBSUB_BATCH_SECONDS_TRESHOLD'])
print("publisher client created")

# Configure batch to publish when 1000 messages or 5 MB of data, or 3 second passed
PublisherBatch = pubsub_v1.PublisherClient(pubsub_v1.types.BatchSettings(
    max_messages=maxmsg,  # default 100
    max_bytes=maxbytes,  # default 1 MB
    max_latency=maxtime  # default 10 ms
))
print(f"publisher-batch created, msg {maxmsg} bytes {maxbytes} t {maxtime}")



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


# called by Sport Bet Api
@app.post('/Batch', response_class=PlainTextResponse)
async def makePublish(request: Request):
    reqData = await request.json()
    topicPath = reqData['topicPath']
    jsonData = reqData['jsonData']
    attributes = reqData.get('attributes')

    if not topicPath:
        print("Batch: missing topic path, End")
        return PlainTextResponse(content="no data", status_code=283)
    if not attributes: attributes = dummyDict
    print(f"Batch: topicPath {topicPath} att {attributes} JsonKeys {jsonData.keys()}")

    err = callPubsubBatch(topicPath, jsonData, attributes)
    if err:
        print(err, " Batch: End")
        return PlainTextResponse(content=err, status_code=284)
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


def callback(future: pubsub_v1.publisher.futures.Future) -> None:
    try: print(f"Batch: pubsub-call msg-id ", future.result())
    except Exception as e: print(f"Batch: future.result() failed: {e}")


def callPubsubBatch(topicPath, jsDict, attributes):
    PromiseArr, jsArr, jsFields = [], None, {}
    for ky in jsDict.keys():
        if not isinstance(jsDict[ky], list): jsFields[ky] = jsDict[ky]
        else: jsArr = jsDict[ky]
    print(f"Batch Arr {jsArr} att {jsFields}")
    if not jsArr: return "empty array"
    
    for js in jsArr:
        msg = dumps({"ArrayItem":js, **jsFields})
        publish_future = PublisherBatch.publish(topicPath, msg.encode("utf-8"), **attributes)
        publish_future.add_done_callback(callback)
        PromiseArr.append(publish_future)

    futures.wait(PromiseArr, timeout=8, return_when=futures.ALL_COMPLETED)
    print(f"Batch: Published messages-batch {len(PromiseArr)}, End")
    return False

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT', 8080)))