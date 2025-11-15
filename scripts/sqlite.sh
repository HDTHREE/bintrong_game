docker run -d \
  --name sqlite-db \
  -v sqlite-data:/data \
  -e SQLITE_DB=/data/mydb.db \
  nouchka/sqlite:latest
