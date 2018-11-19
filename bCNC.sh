#!/usr/bin/env sh

DIR=`dirname $0`/bCNC
PYTHONPATH=${DIR}:${DIR}/lib:${DIR}/plugins
export DIR PYTHONPATH
PYTHON=`which python2`
if [ .$PYTHON = . ]; then
	PYTHON=python
fi
${PYTHON} ${DIR}/__main__.py $*
#python -m cProfile -o bCNC.out ${DIR}/__main__.py $*
