# MongoDB Indexes

## Creating Indexes

```javascript
db.senotypes.createIndex({ uuid: 1 }, { unique: true, name: "uuid_1" });

db.senotypes.createIndex({ sennet_id: 1 }, { name: "sennet_id_1" });

db.senotypes.createIndex(
  { "dataset.uuid": 1, created_timestamp: 1, uuid: 1 },
  { name: "dataset.uuid_1_created_timestamp_1_uuid_1" },
);
```

## Verifying Indexes

```javascript
db.senotypes.getIndexes()
```
