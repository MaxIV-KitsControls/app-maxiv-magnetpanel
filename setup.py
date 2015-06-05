#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="python-magnetpanel",
    version="0.4.3",
    description="QT widget for controlling a magnet circuit.",
    author="Johan Forsberg",
    author_email="johan.forsberg@maxlab.lu.se",
    license="GPLv3",
    url="http://www.maxlab.lu.se",
    include_package_data=True,
    packages=find_packages(),
    scripts=["scripts/ctmagnet",
             "scripts/cttrimcoil"]
)
