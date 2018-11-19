#!/usr/bin/env sh

#Autodetect python version
[ .$PYTHON = . ] && PYTHON=`which python2`
[ .$PYTHON = . ] && PYTHON=python

#Autodetect bCNC install
#If this script is placed in directory with bCNC module it will launch it
#When placed somewhere else (eg. /usr/bin) it will launch bCNC from system
DIR=`dirname $0`
[ -f "${DIR}"/bCNC/__main__.py ] && cd "${DIR}" &&
	echo "Launching bCNC from ${DIR}" ||
	echo "Launching local installation of bCNC"

#Launch
"$PYTHON" -m bCNC $*
