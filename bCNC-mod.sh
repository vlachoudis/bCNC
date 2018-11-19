#!/usr/bin/env sh

DIR=`dirname $0`
cd "${DIR}"
python2 -m bCNC $*
