#!/bin/python2
# -*- coding: ascii -*-

#This is loader script for bCNC, which can also be compiled to .exe

from __future__ import absolute_import
from __future__ import print_function

print("This is currently broken. Use instead: python -m bCNC")

import os
import runpy

bcncpath = os.path.join(
	os.path.dirname(os.path.realpath(__file__)),
	'bCNC/__main__.py'
	)

print("bCNC runpy loader: %s"%(bcncpath))
runpy.run_path(bcncpath, run_name='__main__')
#runpy.run_module('bCNC', run_name='__main__', alter_sys=True)
