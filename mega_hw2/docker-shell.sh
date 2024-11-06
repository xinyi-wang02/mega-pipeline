#!/bin/bash

set -e 

export IMAGE_NAME="mega-hw2-215"
export BASE_DIR="$(pwd)"
export SECRETS_DIR="$(pwd)"/../../../secrets/
 
echo "Building image..."
docker build -t $IMAGE_NAME -f Dockerfile .

docker run --rm --name $IMAGE_NAME -ti \
--mount type=bind,source="$BASE_DIR",target=/app -v "$SECRETS_DIR":/secrets $IMAGE_NAME

