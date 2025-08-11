#!/bin/bash

# Build Consolidated Voice Gateway Layer
set -e

echo "Building Consolidated Voice Gateway Layer..."

# Clean and create directories
rm -rf consolidated_layer_build
mkdir -p consolidated_layer_build/python

# Build dependencies using Docker (x86_64 platform for Lambda)
echo "Installing dependencies in Docker container..."
docker run --rm --platform linux/amd64 \
  -v "$(pwd)/requirements.txt:/requirements.txt" \
  -v "$(pwd)/consolidated_layer_build/python:/python" \
  public.ecr.aws/sam/build-python3.9:latest \
  bash -c "pip install -r /requirements.txt -t /python --no-deps"

# Copy shared code
echo "Copying shared code..."
cp -r python/* consolidated_layer_build/python/

echo "Consolidated layer built successfully!"
echo "Layer content in: $(pwd)/consolidated_layer_build/"

# Check size
echo "Layer size:"
du -sh consolidated_layer_build/

# List contents
echo "Layer contents:"
ls -la consolidated_layer_build/python/ | head -15
