import asyncio
from os import environ
from json import loads
from sys import exit
from signal import signal, SIGTERM
from base64 import b64decode
from schemas import createRow
from flask import Flask, request
from google.cloud.bigquery_storage_v1 import types
from BqStreaming import closeTheStream, ojj, newRowsStream

# called from topic leaveTable and finishHand
# protoc --python_out=. customer_record.proto
streamTresh = 8
app = Flask(__name__)
lockOff = asyncio.Lock()
lockShutdown = asyncio.Lock()
lockCreateNewStream = asyncio.Lock()
print(f"tresh stream {streamTresh}")
print(f"locks: offset {lockOff.locked()} shutdown {lockShutdown.locked()}")


@app.route("/consumeTranses", methods=["POST"])
async def consume_data():
    if lockShutdown.locked() or ojj['shutdown']:
        print(f"ojj-shutd {ojj['shutdown']} lock {lockShutdown.locked()}, END")
        return "already shutting down", 409
    
    envelope = request.get_json()
    if "message" not in envelope:
        print("invalid Pub/Sub message format")
        return "invalid Pub/Sub message format", 200
    
    mesObj = envelope["message"]
    jsonString = b64decode(mesObj['data']).decode("utf-8")
    preRdict = loads(jsonString)
    rdict = preRdict['statsTransByUid']
    kys = list(rdict.keys())

    if len(kys) < 1:
        print("dict empty, offset: ", ojj['offset'])
        return "no transes found", 200

    ii = 0
    proto_rows = types.ProtoRows()
    for uid in rdict.keys():
        for trans in rdict[uid]["tra"]:
            proto_rows.serialized_rows.append(createRow(trans))
            ii = ii + 1
    if ii == 0:
        print(f"no transes found, ii={ii}, offset {ojj['offset']}")
        return "no transes found", 200
    print(f"uids {len(kys)} total transes ii {ii}")
    
    
    async with lockOff:
        req = await crRequestObj(proto_rows, ojj['offset'])
        ojj['offset'] = ojj['offset'] + ii
    
    response_future_1 = await streamSend(req, proto_rows)
    if not response_future_1: return "append failed", 409
    
    try: print(response_future_1.result())
    except Exception as e:
        i, e = 0, str(e)
        print("res.future.result() failed: ", e)
        #fixedOffset = int(e.split(",")[1][-1])
        fixedOffset = genFixedOffset(e)
        while i < 11:
            req = await crRequestObj(proto_rows, fixedOffset)
            response_future = await streamSend(req, proto_rows)
            if not response_future: return "append failed", 409
            try:
                print(response_future.result())
                async with lockOff: ojj['offset'] = fixedOffset
                i = 42
            except Exception as e:
                print(f"res.future.result() failed again: {e}")
                if i == 10:
                    print("max fixed Offset tries reached, END")
                    return "result failed", 409
                i = i + 1
                fixedOffset = genFixedOffset(str(e))

    if ojj['offset'] > streamTresh:
        print("stream tresh reached")
        if lockShutdown.locked() or ojj['shutdown']:
            print("Success. Other req is doing stream shutdown, End")
            return "done", 200
        
        async with lockShutdown:
            print(closeTheStream())
            if not lockCreateNewStream.locked():
                async with lockCreateNewStream:
                    newRowsStream(False)
                    print("new stream created")
            else: print("other request is creating new stream")
                
    print("END, new ofset: ", ojj['offset'])
    return "transes appended", 200




def genFixedOffset(eee):
    errSentence = eee.split(",")[1]
    print("fixOffset: errSentence: ", errSentence)
    num = errSentence.split(" ")[-1]
    print("num: ", num)
    return int(num)

def shutdown_handler(numS, frame):
    ojj['shutdown'] = True
    print(closeTheStream())
    print(f"Signal {numS} offset of current container {ojj['offset']}, End")
    exit(0)

async def crRequestObj(proto_rows, ofs):
    await asyncio.sleep(0)
    req = types.AppendRowsRequest()
    req.offset = ofs
    proto_data = types.AppendRowsRequest.ProtoData()
    proto_data.rows = proto_rows
    req.proto_rows = proto_data
    return req

async def streamSend(req, proto_rows):
    try: response_future_1 = ojj['rStream'].send(req)
    except Exception as e:
        print(f"append rows failed: {e}")
        if lockCreateNewStream.locked():
        #if ojj['runNew']:
            async with lockOff:
                req = await crRequestObj(proto_rows, ojj['offset'])
                ojj['offset'] = ojj['offset'] + 1
            print("already recreating stream")
            try: response_future_1 = ojj['rStream'].send(req)
            except Exception as e:
                print(f"appendR failed again ByOther: {e}")
                return False
            print("newRows Stream ByOther success")
            return response_future_1
        #ojj['runNew'] = True
        async with lockCreateNewStream:
            newRowsStream(False)
            req = await crRequestObj(proto_rows, 0)
        async with lockOff: ojj['offset'] = ojj['offset'] + 1
        print("cr new Stream!")
        try: response_future_1 = ojj['rStream'].send(req)
        except Exception as e:
            print("appendR failed again ByMe: ", e)
            return False
        print("newRows Stream ByMe success")
    return response_future_1

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(environ.get('PORT', 8080)))
else:
    signal(SIGTERM, shutdown_handler)