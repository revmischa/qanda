#!/bin/bash

TARGET_DIR=qanda

pip3.6 install -t $TARGET_DIR --upgrade $@
rm -fr $TARGET_DIR/*.dist-info
rm -fr $TARGET_DIR/__pycache__
