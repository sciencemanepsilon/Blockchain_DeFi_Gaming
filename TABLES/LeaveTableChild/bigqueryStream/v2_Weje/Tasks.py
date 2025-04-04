from datetime import datetime, timedelta
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

client = tasks_v2.CloudTasksClient()
parent = client.queue_path(
    "weje-2023", "europe-central2", "LeaveTabChildren-UpdateStats"
)
url = "https://leavechild-update-stats-dhxeo2bzqq-zf.a.run.app"


def makeTASK(in_seconds):
    timestampProto = timestamp_pb2.Timestamp()
    timestampProto.FromDatetime(
        datetime.utcnow() + timedelta(seconds=in_seconds)
    )
    res = client.create_task(request={
        "parent": parent,
        "task": {
            "schedule_time": timestampProto,
            "http_request":{"url":url, "http_method":tasks_v2.HttpMethod.GET}
    }})
    if res.name:
        tNum = res.name.split('/')[7]
        print(f"task {tNum}:{url}\n{res.create_time} --> {res.schedule_time}")
    else: print("task failed")
    return 0