docker run --rm -d \
  --name localstack \
  -p 4566:4566 \
  -p 4571:4571 \
  -e SERVICES=s3,dynamodb \
  -e DEFAULT_REGION=us-east-1 \
  -e DEBUG=1 \
  localstack/localstack:latest
