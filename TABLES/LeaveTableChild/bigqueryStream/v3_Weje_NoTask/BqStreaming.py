from schemas import reqTemplate
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.cloud.bigquery_storage_v1 import writer

pid = "weje-2023"
dataSet = "WejeLive"
table = "Transactions"

def crWriteStream(write_client, parent):
    write_stream = types.WriteStream()
    write_stream.type_ = types.WriteStream.Type.PENDING
    write_stream = write_client.create_write_stream(parent=parent,write_stream=write_stream)
    return write_stream

def newRowsStream(init):
    write_client = bigquery_storage_v1.BigQueryWriteClient()
    parent = write_client.table_path(pid, dataSet, table)
    write_stream = crWriteStream(write_client, parent)
    append_rows_stream = writer.AppendRowsStream(write_client, reqTemplate(write_stream))
    if init:
        ojj = {
            "offset":0, "shutdown":False, "wrClient":write_client, "runNew":False,
            "rStream":append_rows_stream, "parent":parent, "wrStream":write_stream
        }
        print("append_rows_stream created")
        return ojj
    else:
        override(write_client, append_rows_stream, parent, write_stream)
        print("append_rows_stream overriden")
        return 0

ojj = newRowsStream(True)


def override(a, b, c, d):
    ojj['offset'], ojj['wrClient'] = (0, a)
    ojj['runNew'], ojj['rStream'] = (False, b)
    ojj['parent'], ojj['wrStream'] = (c, d)
    return 0


def closeTheStream():
    try:
        #append_rows_stream.close()
        ojj['rStream'].close()
        #write_client.finalize_write_stream(name=write_stream.name)
        ojj['wrClient'].finalize_write_stream(name=ojj['wrStream'].name)
    except Exception as e:
        print(f"stream close/finalize failed: {e}")
        return "stream close/finalize failed"
    
    commitReq = types.BatchCommitWriteStreamsRequest()
    #commitReq.parent = parent
    commitReq.parent = ojj['parent']
    #commitReq.write_streams = [write_stream.name]
    commitReq.write_streams = [ojj['wrStream'].name]
    #write_client.batch_commit_write_streams(commitReq)
    ojj['wrClient'].batch_commit_write_streams(commitReq)
    return "Write stream committed"
