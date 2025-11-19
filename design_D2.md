```mermaid
flowchart TD
    subgraph K8S_Cluster["K8S Cluster"]
        direction TB

        subgraph API_Services[" "]
            DB[(Database)]
            SERVER[Backend API]
            FRONTEND[Frontend]
            GAMESERVER[Game Server]
            BUCKET[[File Bucket]]
        end

        subgraph Gateway["gateway"]
            SOCKETS((sockets))
            SERVES((serves))
        end
    end

    subgraph Users["users"]
        CLIENT[client]
    end

    SERVER -->|spawns| GAMESERVER
    GAMESERVER -->|updates UI| FRONTEND
    SERVER -->|queries/reads/writes| DB
    FRONTEND -->|API calls| SERVER
    SERVER -->|stores/retrieves files| BUCKET

    SOCKETS <-->|WebSocket forward| GAMESERVER
    FRONTEND -->|HTTP serve| SERVES

    CLIENT <-->|WebSocket connection| SOCKETS
    SERVES -->|HTTP request| CLIENT
```

Arrows are labelled indicating the action being take. Circles represent the different application layer protocols that will be used to serve the game and sync the game with the server. Hard rectangles are machines that are involved in starting or participating in the game loop. The cylinder and double rectangle represent the database and object store respectively. Note that the entire section listed under the k8s cluster and gateway are expected to scale and load balance in a production deployment.
