from asyncio import sleep
from google.cloud import bigquery
from ElasticFunc import schemaSess, schemaUsersData
BQ = bigquery.Client()

schemaSessions = []
for sess in schemaSess:
    sessArr = sess.split("-")
    schemaSessions.append(
        bigquery.SchemaField(sessArr[0], sessArr[1], mode=sessArr[2])
    )

schemaUserData = []
for user in schemaUsersData:
    sessArr = user.split("-")
    schemaUserData.append(
        bigquery.SchemaField(sessArr[0], sessArr[1], mode=sessArr[2])
    )

async def writeBQ(dataName, tid, jsonDict, schema): # 1500 load jobs per table per day
    await sleep(0)
    print(f"writing {dataName} to BigQuery..")
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        #write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE default is WRITE_APPEND
    )
    BQ.load_table_from_json(jsonDict, tid, location="EU", job_config=job_config)
    #load_job = BQ.load_table_from_json(jsonDict, tid, location="US", job_config=job_config)
    #load_job.result()
    print(f"{dataName} done")
    return 0