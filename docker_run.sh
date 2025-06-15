#!/bin/bash

# CESIUM token for the application
CESIUM_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkZjZmODk0My0xM2FjLTRjOTItODQzMC00ZjJlNjIzZDg3ZjQiLCJpZCI6MzExMDc5LCJpYXQiOjE3NDk2MDU0NDV9.OUGsQDARmCnWT3cqF1YkTabFdC-_EmS-7TO-0aTQ03o"

# Function to print colored output
print_status() {
    echo -e "\e[1;34m==>\e[0m $1"
}

# Function to print error messages
print_error() {
    echo -e "\e[1;31mError:\e[0m $1"
}

# Function to print success messages
print_success() {
    echo -e "\e[1;32mSuccess:\e[0m $1"
}

# Stop and remove all containers using the image
print_status "Stopping and removing containers using pdharmendra/uavlogviewer:arm64..."
CONTAINERS=$(docker ps -a --filter ancestor=pdharmendra/uavlogviewer:arm64 -q)
if [ ! -z "$CONTAINERS" ]; then
    docker rm -f $CONTAINERS
    print_success "Containers removed successfully"
else
    print_status "No containers found using this image"
fi

# Remove the old image
print_status "Removing old image pdharmendra/uavlogviewer:arm64..."
if docker rmi pdharmendra/uavlogviewer:arm64; then
    print_success "Old image removed successfully"
else
    print_error "Failed to remove image or image doesn't exist"
fi

# Build new image
print_status "Building new image..."
if docker build --platform linux/arm64 -t pdharmendra/uavlogviewer:arm64 .; then
    print_success "New image built successfully"
else
    print_error "Failed to build new image"
    exit 1
fi

# Run new container
print_status "Starting new container..."
if docker run -e VUE_APP_CESIUM_TOKEN=$CESIUM_TOKEN -p 8080:8080 -d pdharmendra/uavlogviewer:arm64; then
    print_success "Container started successfully"
    print_status "Application is running at http://localhost:8080"
else
    print_error "Failed to start container"
    exit 1
fi

# Print container ID
CONTAINER_ID=$(docker ps --filter ancestor=pdharmendra/uavlogviewer:arm64 -q)
if [ ! -z "$CONTAINER_ID" ]; then
    print_status "Container ID: $CONTAINER_ID"
fi