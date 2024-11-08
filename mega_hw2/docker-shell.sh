#!/bin/bash

set -e 

export IMAGE_NAME="mega-hw2-215"
export BASE_DIR="$(pwd)"
export SECRETS_DIR="$(pwd)"/../../secrets/
export GCS_BUCKET_NAME="mega-pipeline-bucket-215"
export GCP_PROJECT="caramel-brook-434717-p6"
export GCP_ZONE="us-central1-a"
export GOOGLE_APPLICATION_CREDENTIALS="/secrets/mega-pipeline.json"
 
echo "Building image..."
docker build -t $IMAGE_NAME .

echo "Running container"
docker run --rm --name $IMAGE_NAME -ti \
-v "$BASE_DIR":/app \
-v "$SECRETS_DIR":/secrets \
-e GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS \
-e GCP_PROJECT=$GCP_PROJECT \
-e GCP_ZONE=$GCP_ZONE \
-e GCS_BUCKET_NAME=$GCS_BUCKET_NAME $IMAGE_NAME

