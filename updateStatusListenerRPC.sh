#!/bin/bash
python -m grpc_tools.protoc \
    --proto_path=x22_fleet/Library \
    --python_out=x22_fleet/Library \
    --grpc_python_out=x22_fleet/Library \
    x22_fleet/Library/statuslistener.proto