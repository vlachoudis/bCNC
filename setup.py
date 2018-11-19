from setuptools import setup, find_packages

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f:
	long_description = f.read()

setup(
	name = "bCNC",
	version = "0.9.14.20",
	description='Swiss army knife for all your CNC/g-code needs',
	license="GPL",
	long_description=long_description,
	long_description_content_type='text/markdown',
	packages = find_packages(),
	author = "Harvie",
	#author_email='foomail@foo.com',
	url="https://github.com/vlachoudis/bCNC",
	include_package_data=True,
	install_requires = [
		'pyserial>=3.4',
		'numpy>=1.15.4',
		'opencv-python>=3.4.2.17',
		'Pillow>=5.3.0',
	],

	entry_points = {
		'console_scripts': [
			#'bCNC = {package}.{module}:{main_function}',
			#'bCNC = bCNC.bCNC:main',
			'bCNC = bCNC.__main__:main',
		]
	}
)
