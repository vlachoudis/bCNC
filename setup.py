from setuptools import setup, find_packages
import sys #added for python2 support
print("Running bCNC setup...")

with open("README.md", "r") as fh:
	long_description = fh.read()

if sys.version_info[0] >= 3:
	opencv_version = '4.4.0.46' # Recent version for Puthon 3
else: #python version lower then 3 compatability
	opencv_version ='4.2.0.32' # use the last opencv version for python 2.7

setup(
	name = "bCNC",
	version = "0.9.14.317",
	license="GPLv2",
	description='Swiss army knife for all your CNC/g-code needs',
	long_description=long_description,
	long_description_content_type="text/markdown",
	packages = find_packages(),
	author = 'Vasilis Vlachoudis',
	author_email='vvlachoudis@gmail.com',
	url="https://github.com/vlachoudis/bCNC",
	include_package_data=True,
	#python_requires="<3.0",
	install_requires = [
		"pyobjc ; sys_platform == 'darwin'",
		"pyobjc-core; sys_platform == 'darwin'",
		"pyobjc-framework-Quartz; sys_platform == 'darwin'",

		"pyserial ; sys_platform != 'win32'",	#Windows XP can't handle pyserial newer than 3.0.1 (it can be installed, but does not work)
		"pyserial<=3.0.1 ; sys_platform == 'win32'",
		'numpy>=1.12',
		'Pillow>=4.0',
		'opencv-python==%s ; ("arm" not in platform_machine) and ("aarch64" not in platform_machine)' % (opencv_version),	#Note there are no PyPI OpenCV packages for ARM (Raspberry PI, Orange PI, etc...)
	],

	entry_points = {
		'console_scripts': [
			#'bCNC = {package}.{module}:{main_function}',
			#'bCNC = bCNC.bCNC:main',
			'bCNC = bCNC.__main__:main',
		]
	},

	classifiers=[
		"Development Status :: 4 - Beta",
		"License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
		"Operating System :: OS Independent",
		"Topic :: Multimedia :: Graphics :: 3D Modeling",
		"Topic :: Multimedia :: Graphics :: Capture",
		"Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
		"Topic :: Multimedia :: Graphics :: Graphics Conversion",
		"Topic :: Multimedia :: Graphics :: Viewers",
		"Topic :: Scientific/Engineering",
		"Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
		"Topic :: Terminals :: Serial",
		"Natural Language :: Dutch",
		"Natural Language :: English",
		"Natural Language :: German",
		"Natural Language :: Spanish",
		"Natural Language :: Portuguese",
		"Natural Language :: Portuguese (Brazilian)",
		"Natural Language :: French",
		"Natural Language :: Italian",
		"Natural Language :: Japanese",
		"Natural Language :: Korean",
		"Natural Language :: Russian",
		"Natural Language :: Chinese (Simplified)",
		"Natural Language :: Chinese (Traditional)",
	]
)
