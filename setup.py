#!/usr/bin/python
from setuptools import setup

setup(
	name = 'CCBUpgrade',
	version = '0.1.0',
	author = 'Sidebolt Studios',
	author_email = 'support@sidebolt.com',
	scripts = ['bin/ccbup.py'],
	url = 'http://sidebolt.com/',
	install_requires = ['dimensions==0.0.2'],
	description = 'Converts CocosBuilder 3 files to the SpriteBuilder 1.0 format.'
)
