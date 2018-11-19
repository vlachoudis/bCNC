from setuptools import setup, find_packages

setup(
	name = "bCNC",
	version = "0.9.14.19",
	description='Swiss army knife for all your CNC/g-code needs',
	license="GPL",
	#long_description=long_description,
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
