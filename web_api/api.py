import json

import redis
import uvicorn
from fastapi import FastAPI
import requests
from starlette.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/redis")
async def location_redis():
    """
    An API demo how to query latest position from redis.
    :return:
    """
    # https://docs.redis.com/latest/rs/references/client_references/client_python/
    r = redis.Redis(
        host='localhost',
        port='6379',
        password='xxxxxxxx',
        db=1)

    # get data from redis
    keys = r.keys('*')
    values = r.mget(keys)

    # current location data
    locations = [
        {
            'veh_id': keys[i].decode(),
            'loc': values[i].decode(),
        } for i in range(len(keys))]
    locations.sort(key=lambda x: x['veh_id'])

    return {
        'size': len(locations),
        'data': locations
    }


@app.get("/ksqldb")
async def location_ksqldb():
    """
    An API demo how to query latest position from ksqlDB directly.
    :return:
    """

    # send request to ksqldb using rest api
    # https://docs.ksqldb.io/en/latest/developer-guide/ksqldb-rest-api/query-endpoint/
    resp = requests.post(
        'http://ksqldb-server:8088/query',
        headers={"Accept": "application/vnd.ksql.v1+json"},
        data=json.dumps(
            {
                'ksql': 'select * from bus_current;',
                'streamsProperties': {}
            })).json()

    locations = [
        {
            'veh_id': data['row']['columns'][0],
            'loc': data['row']['columns'][1]
        } for data in resp[1:]]  # resp[1:] to skip headers
    locations.sort(key=lambda x: x['veh_id'])

    return {
        'size': len(locations),
        'data': locations
    }


@app.get("/ksqldb-push")
async def location_ksqldb_push():
    """
    An API demo how to push query position changes from ksqlDB directly.

    How to run push query against ksqldb server:
    https://docs.ksqldb.io/en/latest/developer-guide/ksqldb-rest-api/streaming-endpoint/

    curl -X "POST" "http://ksqldb-server:8088/query-stream" \
        -d $'{
      "sql": "SELECT * FROM bus_current EMIT CHANGES;",
      "streamsProperties": {}
    }'
    :return:
    """

    def get_streaming_data():
        with requests.post(
                'http://ksqldb-server:8088/query-stream',
                stream=True,
                data=json.dumps(
                    {
                        'sql': 'select * from bus_current emit changes;',
                        'streamsProperties': {}
                    })) as r:
            for chunk in r.iter_content(chunk_size=1024 * 8):
                chunk = chunk.decode()
                if chunk.startswith('{'):
                    # header
                    # {"queryId":"xxxx",
                    # "columnNames":["VEH_ID","POSITION","TS"],
                    # "columnTypes":["INTEGER","STRING","BIGINT"]}
                    continue

                veh_id, loc = json.loads(chunk)
                yield f"{json.dumps({'veh_id': veh_id, 'loc': loc})}\n"

    return StreamingResponse(content=get_streaming_data())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
