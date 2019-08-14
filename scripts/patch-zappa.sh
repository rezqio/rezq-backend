#!/usr/bin/env bash

set -e

cd "$( dirname "${BASH_SOURCE[0]}" )"

cd ..

FILE='.venv/lib/python3.6/site-packages/zappa/handler.py'

REPLACE='^import sys$'
INSERT='import sys; sys.path.insert(0, "rezq_backend")'

echo -n 'Patching zappa handler.py ...'

sed -i.bak "s/$REPLACE/$INSERT/" $FILE

echo ' done!'
