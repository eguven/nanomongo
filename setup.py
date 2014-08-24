#!/usr/bin/env python
# -*- coding: utf-8 -*-
import multiprocessing  # http://bugs.python.org/issue15881#msg170215

import nanomongo
import six

from setuptools import setup

setup(
    name='nanomongo',
    version=nanomongo.__version__,
    description='Minimal Python ODM for MongoDB',
    long_description=open('README.rst').read(),
    author=six.u('Eren Güven'),
    author_email='erenguven0@gmail.com',
    url='https://github.com/eguven/nanomongo',
    install_requires=['pymongo >= 2.5', 'six'],
    packages=['nanomongo'],
    setup_requires=['nose'],
    test_suite='nose.main',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
