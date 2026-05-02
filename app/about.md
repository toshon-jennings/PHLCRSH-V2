# About the app

The app downloads geoparquet data from s3 blob storage (cloudflare r2 because it's easy and cheap), loads it into a local duckdb instance inside of a wasm container (thx duckdb-wasm) as a view, and persists the data locally in OPFS (TODO: link). (Better - store the raw data in OPFS, then load etc.)

## DuckDB WASM Rationale

Heavy, but single-user web applications where you don't want to pay for compute. (Do some rough calculations). Data must be intensive enough to warrant (otherwise js in-memory is fine).

## OPFS Rationale

Big data means all sorts of things. 30 years ago, FMV (full motion video) was an everyday term amongst gamers and the tech-inclined because (insert exact size) was considers big data. 

Some data is too big to travel quickly and reliably across a network, from you to the cloud and back, so keeping that data transfer on the same machine betwee processes is much more performant. Other data is currently too big to download (or to want to download because it contains much more data than you actually ened) onto one machine (insert size), and so it goes back up into the cloud and is contextually queried by clients. It's the whole fat client <-> thin server cycle, just from a data side of things.
