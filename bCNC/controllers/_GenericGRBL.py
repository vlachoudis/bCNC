# Generic GRBL motion controller definition
# All GRBL versions inherit features from this one

from __future__ import absolute_import
from __future__ import print_function
from _ControllerGeneric import _ControllerGeneric

class _GenericGRBL(_ControllerGeneric):
	def test(self):
		print("test supergen grbl")
