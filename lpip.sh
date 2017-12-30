#!/bin/bash

pip install -t handler --upgrade $@
rm -fr handler/*.dist-info
rm -fr handler/__pycache__
