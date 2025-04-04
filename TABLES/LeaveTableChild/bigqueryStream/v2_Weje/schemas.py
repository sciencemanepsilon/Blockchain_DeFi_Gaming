import transData_pb2
from datetime import datetime
from google.protobuf import descriptor_pb2
from google.cloud.bigquery_storage_v1 import types

def reqTemplate(write_stream):
    request_template = types.AppendRowsRequest()
    request_template.write_stream = write_stream.name
    proto_schema = types.ProtoSchema()

    proto_descriptor = descriptor_pb2.DescriptorProto()
    transData_pb2.CustomerRecord.DESCRIPTOR.CopyToProto(proto_descriptor)
    proto_schema.proto_descriptor = proto_descriptor

    protoData = types.AppendRowsRequest.ProtoData()
    protoData.writer_schema = proto_schema
    
    request_template.proto_rows = protoData
    return request_template

def createRow(tra):
    row = transData_pb2.CustomerRecord()
    row.uid = tra['uid']
    row.name = tra['name']
    row.From = tra['from']
    row.coinsAmount = tra['coinAm']
    row.fee = tra['fee']
    row.date = datetime.utcnow().replace(microsecond=0).isoformat()
    row.firebaseID = tra['fireId']
    row.from_id = tra['fromId']
    row.currency = tra['currency']
    return row.SerializeToString()
