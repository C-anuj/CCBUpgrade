#!/usr/bin/python
from setuptools import setup

setup(
	name = 'ssgame',
	version = '0.1.0',
	author = 'Sidebolt Studios',
	author_email = 'contact@sidebolt.com',
	packages = [
		'ssgame',
	],
	package_data = {
		'ssgame': ['views/*.js'],
	},
	scripts = ['bin/ssgamed.py', 'bin/ssgame_schema.py', 'bin/sssaled.py', 'bin/ssleagued.py'],
	url = 'http://eric.local/',
	description = 'Social slots game libraries and daemon'
)
