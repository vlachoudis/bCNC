from setuptools import setup, find_packages

print("Running bCNC setup...")

with open("README.md", "r") as fh:
	long_description = fh.read()

setup(
	name = "bCNC",
	version = "0.9.14.57",
	license="GPLv2",
	description='Swiss army knife for all your CNC/g-code needs',
	long_description=long_description,
	long_description_content_type="text/markdown",
	packages = find_packages(),
	author = 'Vasilis Vlachoudis',
	author_email='vvlachoudis@gmail.com',
	url="https://github.com/vlachoudis/bCNC",
	include_package_data=True,
	python_requires="<3.0",
	install_requires = [
		'pyserial<=3.0.1',	#Windows XP can't handle pyserial newer than 3.0.1
		'numpy>=1.12',
		'Pillow>=4.0',
		#'opencv-python>=2.4',	#Note there are no PyPI OpenCV packages for ARM (Raspberry PI, Orange PI, etc...)
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
