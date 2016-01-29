#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="python-magnetpanel",
    version="0.4.8",
    description="QT widget for controlling a magnet circuit.",
    author="Johan Forsberg",
    author_email="johan.forsberg@maxlab.lu.se",
    license="GPLv3",
    url="http://www.maxlab.lu.se",
    include_package_data=True,
    packages=find_packages(),
    package_data={"":["*.ui"]},
    #scripts=["scripts/ctmagnet",
    #         "scripts/cttrimcoil"]
    entry_points = {"console_scripts" : ["cttrimcoil = magnetpanel:trimcoil_main" ,  "ctmagnet = magnetpanel:magnet_main"]}
)
