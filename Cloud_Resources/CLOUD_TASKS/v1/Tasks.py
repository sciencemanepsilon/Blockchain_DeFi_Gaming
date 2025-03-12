from datetime import datetime, timedelta
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2, duration_pb2
from myFunc import pid, requestTimeoutForAllTasks
from json import dumps
client = tasks_v2.CloudTasksClient()

def scheduleTask(url, inSec, queName, region, payload):
    # duration: controling target request timeout
    duration = duration_pb2.Duration()
    duration.FromSeconds(requestTimeoutForAllTasks)

    timestampProto = timestamp_pb2.Timestamp()
    timestampProto.FromDatetime(
        datetime.utcnow() + timedelta(seconds=inSec)
    )
    if isinstance(payload, dict):
        rDict = {
            "url": url,
            "body": dumps(payload).encode(),
            "http_method": tasks_v2.HttpMethod.POST,
            "headers": {"Content-type":"application/json"}
        }
    else:
        rDict = {
            "url":url + payload,
            "http_method":tasks_v2.HttpMethod.GET
        }
    res1 = client.create_task(request={
        "task": {
            "http_request":rDict,
            "schedule_time":timestampProto,
            "dispatch_deadline": duration
        },
        "parent":client.queue_path(pid, region, queName)
    })
    if res1.name:
        print(f"taskRes {res1.name}, {res1.http_request.url}")
        return 0
    else:
        print(f"task {url} failed: {res1}")
        return "task schedule failed"