# StreamingService 101

Use ksqlDB to bring realtime data to your project.


## Batch/Realtime architecures

We only focus on the differences between the batch architecture and the realtime architecture, we will not cover any topics like Lambda architecture, Kappa architecture.

- Batch based architecture
  ```
  Data -> Kafka -> Offline DB -> Batch/ETL    -> Online DB -> Web app
                  |---------- minutes/hours------------|
  ```

- Realtime based architecure
  ```
  Data -> Kafka -> Stream Processing -> Kafka -> Online DB -> Web app
                  |---------- milliseconds/seconds-----|
  ```

## ksqlDB vs "DB"

A lot of new Database technologies, this table will highlight the key differences between ksqlDB and online/offline databases. This may not apply to some NoSQL, New SQL, HTAP databases.

| Diffs              | ksqlDB                  | Online DB                 | Offline DB                |
| ------------------ | ----------------------- | ------------------------- | ------------------------- |
| Input              | Kafka                   | Insert/Bulk load          | Insert/Bulk load          |
| Output             | Kafka                   | Instant response          | Table or Instant response |
| Storage            | Kafka, RocksDB          | Data format on local disk | Avro, ORC, Parquet        |
| Index              | Not needed              | Highly depends on Index   | Not really use Index      |
| Trigger            | Realtime                | Online request            | Batch job                 |
| Scalability        | High                    | Low-Mid                   | Mid-High                  |
| Query QPS          | Low                     | High                      | Low                       |
| Query scale        | Millions/**Second**     | Millions/Table            | Billions/Table            |
| Query time         | Endless or Milliseconds | Milliseconds              | Minutes                   |
| Query: Select      | Key, Range              | All                       | All                       |
| Query: Aggregation | Realtime agg            | -                         | Batched agg               |
| Query: Transaction | -                       | Yes                       | -                         |
| Query: Join        | Limited/co-partition    | Yes (Not recommend)       | Yes                       |

## Demo

Using [vehicle-positions](https://digitransit.fi/en/developers/apis/4-realtime-api/vehicle-positions/) for demo.

### 1. Prerequisite

  Check `./docker-compose.yml`

  ```
  # install connector plugins
  mkdir -p confluent-hub-components
  confluent-hub install confluentinc/kafka-connect-mqtt:latest --component-dir confluent-hub-components
  confluent-hub install confluentinc/kafka-connect-jdbc:10.6.0 --component-dir confluent-hub-components
  confluent-hub install jcustenborder/kafka-connect-redis:0.0.4 --component-dir confluent-hub-components

  # start services
  docker-compose up -d

  # create topic in multiple partitions
  kafka-topics --bootstrap-server broker:9092 --create --topic bus_raw --replication-factor 1 --partitions 3
  ```
### 2. Source data into Kafka

  Check `./connectors/mqtt-source.json`

  ```
  # create mqtt source connector
  curl -X POST http://localhost:8083/connectors \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    --data "@./connectors/mqtt-source.json" | jq

  # show connector status
  curl -X GET http://localhost:8083/connectors/mqtt-source/status | jq
  ```
### 3. Create stream in ksqlDB
    
  Check `./ksqldb/create_stream.sql`

  ```
  docker exec -it ksqldb-cli ksql http://ksqldb-server:8088 -f /ksqldb/create_stream.sql
  ```
### 4. Create table in ksqlDB to calculate latest position.

  Check `./ksqldb/create_table_bus_current.sql`. The one with `_sr` uses AVRO inside schema-registry which is important for sink connectors needs a schema.

  ```
  docker exec -it ksqldb-cli ksql http://ksqldb-server:8088 -f /ksqldb/create_table_bus_current.sql
  ```
### 5. Sink connector (Redis/Postgres).

  Redis: `./connectors/redis-sink.json`
  ```
  # create redis sink connector
  curl -X POST http://localhost:8083/connectors \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    --data "@./connectors/redis-sink.json" | jq

  # show connector status
  curl -X GET http://localhost:8083/connectors/redis-sink/status | jq
  ```

  Postgres: `./connectors/postgres-sink.json`
  ```
  # create postgres sink connector
  curl -X POST http://localhost:8083/connectors \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    --data "@./connectors/postgres-sink.json" | jq

  # show connector status
  curl -X GET http://localhost:8083/connectors/postgres-sink/status | jq
  ```

  Postgres Suppressed: `./connectors/postgres-sink-10s.json`
  ```
  # create postgres sink connector with suppress
  curl -X POST http://localhost:8083/connectors \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    --data "@./connectors/postgres-sink-10s.json" | jq

  # show connector status
  curl -X GET http://localhost:8083/connectors/postgres-sink-10s/status | jq
  ```

### 6. API demo
    
  Check inside `./web_api/api.py`.

  The API deployment runs in debug mode, for production deployment please refer to [this Fast API document](https://fastapi.tiangolo.com/deployment/concepts/).

  Endpoints with different parameters. See full Swagger document: http://localhost:8000/docs
  
  | Endpoint                                    | DB             | Desc                                                     |
  | ------------------------------------------- | -------------- | -------------------------------------------------------- |
  | http://localhost:8000/redis                 | Redis          | Redis connector, High update traffic                     |
  | http://localhost:8000/pg/bus_current_sr     | Postgres       | JDBC connector, High update traffic                      |
  | http://localhost:8000/pg/bus_current_sr_10s | Postgres       | JDBC connector, Low update traffic, suppressed by kslqdb |
  | http://localhost:8000/ksqldb                | ksqlDB/RocksDB | Latest status from RocksDB                               |
  | http://localhost:8000/ksqldb-push           | ksqlDB/Kafka   | Streaming API                                            |

### 7. Finish

  ```
  docker-compose down -v
  ```

## References:
- [Confluent Course: KSQLDB 101](https://developer.confluent.io/learn-kafka/ksqldb/intro/)
- https://digitransit.fi/en/developers/apis/4-realtime-api/vehicle-positions/