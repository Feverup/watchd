#!/usr/bin/env python

from distutils.core import setup

setup(
    name = 'watchd',
    version = '0.9',
    description = 'Alarms enabled metric monitoring service',
    license = 'Apache License (2.0)',
    url = 'https://github.com/Feverup/watchd',
    author = 'Javier Palacios',
    author_email = 'javier.palacios@feverup.com',
    packages = ['watchd'],
    install_requires = [ 'boto' ],
    scripts = [ 'watchd.py' ]
    )

