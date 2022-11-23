# KikiRara

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

| Diffs              | ksqlDB               | Online DB                 | Offline DB                |
| ------------------ | -------------------- | ------------------------- | ------------------------- |
| Input              | Kafka                | Insert/Bulk load          | Insert/Bulk load          |
| Output             | Kafka                | Instant response          | Table or Instant response |
| Storage            | Kafka, RocksDB       | Data format on local disk | Avro, ORC, Parquet        |
| Index              | Not needed           | Highly depends on Index   | Not really use Index      |
| Trigger            | Realtime             | Online request            | Batch job                 |
| Scalability        | High                 | Low                       | Mid/High                  |
| QPS                | Low                  | High                      | Low                       |
| Data scale         | Millions/**Second**  | Millions/Table            | Billions/Table            |
| Data latency       | Milliseconds         | Milliseconds              | Minutes                   |
| Query: Select      | Key, Range           | All                       | All                       |
| Query: Aggregation | Realtime agg         | -                         | Batched agg               |
| Query: Transaction | -                    | Yes                       | -                         |
| Query: Join        | Limited/co-partition | Yes (Not recommend)       | Yes                       |

## Demo

Using [vehicle-positions](https://digitransit.fi/en/developers/apis/4-realtime-api/vehicle-positions/) for demo.

### 1. Prerequisite
    ```
    # install connector plugins
    mkdir -p confluent-hub-components
    confluent-hub install confluentinc/kafka-connect-mqtt:latest --component-dir confluent-hub-components
    confluent-hub install confluentinc/kafka-connect-jdbc:10.6.0 --component-dir confluent-hub-components
    confluent-hub install jcustenborder/kafka-connect-redis:0.0.4 --component-dir confluent-hub-components

    # create source topic and license topic
    kafka-topics --bootstrap-server broker:9092 --create --topic _confluent-command --partitions 3 --replication-factor 1
    ```
### 2. Source data into Kafka
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
    ```
    docker exec -it ksqldb-cli ksql http://ksqldb-server:8088 -f /ksqldb/create_stream.sql
    ```
### 4. Create table in ksqlDB to calculate latest position.
    ```
    docker exec -it ksqldb-cli ksql http://ksqldb-server:8088 -f /ksqldb/create_table_bus_current.sql
    ```
### 5. Sink connector.
    ```
    # create recis sink connector
    curl -X POST http://localhost:8083/connectors \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json' \
      --data "@./connectors/redis-sink.json" | jq

    # show connector status
    curl -X GET http://localhost:8083/connectors/redis-sink/status | jq
    ```
### 6. API demo
    ```
    cd web_api
    
    # start fast API server.
    python api.py
    ```
    There are 3 endpoints available from this python server.
    - http://localhost:8000/redis
    - http://localhost:8000/ksqldb (pull query)
    - http://localhost:8000/ksqldb-push (push query)
### 7. Finish

## Todo:
- [ ] API behaviors when ksqlDB rebalance

## References:
- [Confluent Course: KSQLDB 101](https://developer.confluent.io/learn-kafka/ksqldb/intro/)
- https://digitransit.fi/en/developers/apis/4-realtime-api/vehicle-positions/