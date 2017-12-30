#!/bin/bash

pip3 install -t handler --upgrade $@
rm -r handler/*.dist-info
rm -r handler/__pycache__
