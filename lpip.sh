#!/bin/bash

pip install -t handler --upgrade $@
rm -r handler/*.dist-info
rm -r handler/__pycache__
