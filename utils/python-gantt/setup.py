#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#from distutils.core import setup, Extension

from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

setup (
    name = 'python-gantt',
    version = '0.6.0',
    author = 'Alexandre Norman',
    author_email = 'norman@xael.org',
    license ='gpl-3.0.txt',
    keywords="gantt, graphics, scheduling, project management",
    # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    platforms=[
        "Operating System :: OS Independent",
        ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Scientific/Engineering :: Visualization",
        ],
    packages=['gantt'],
    url = 'http://xael.org/pages/python-gantt-en.html',
    bugtrack_url = 'https://bitbucket.org/xael/python-gantt',
    description = 'This is a python class to create gantt chart using SVG.',
    long_description=long_description,
    install_requires=[
        'svgwrite>=1.1.6',
        'clize>=2.0',
        'python-dateutil>=2.4'
        ],
    zip_safe = True, 
    )



