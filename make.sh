#!/bin/bash
set -e -u

make -C doc html
echo
echo "Hint: It's a good idea to run \"`dirname $0`/test.sh\" ;)"
