# Copyright (c) 2008-2011 by Enthought, Inc.
# All rights reserved.
import os

from setuptools import setup, find_packages

with open('README.rst') as fid:
    long_description = fid.read()

version_path = os.path.abspath('version.txt')
try:
    with open(version_path) as fid:
        version_str = fid.read().strip()
except IOError as err:
    raise IOError("File indicating the version could not be read: {}".format(version_path))


setup(
    name='meta',
    version=version_str,
    author='Sean Ross-Ross, Enthought Inc.',
    author_email='srossross@enthought.com',
    maintainer='Sean Ross-Ross',
    maintainer_email='enthought-dev@enthought.com',
    url='http://srossross.github.com/Meta',

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries"],
    description='Byte-code and ast programming tools',
    long_description=long_description,
    include_package_data=True,
    license='BSD',
    packages=find_packages(),
    platforms=["Windows", "Linux", "Mac OS-X", "Unix", "Solaris"],
    entry_points={'console_scripts': ['depyc = meta.scripts.depyc:main']})
