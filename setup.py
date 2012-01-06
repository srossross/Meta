# Copyright (c) 2008-2011 by Enthought, Inc.
# All rights reserved.

from setuptools import setup, find_packages

try:
    long_description = open('README.rst').read()
except IOError as err:
    long_description = str(err)

try:
    version_str = open('version.txt').read()
except IOError as err:
    version_str = '???'


setup(
    name='meta',
    version=version_str,
    author='Sean Ross-Ross, Enthought Inc.',
    author_email='srossross@enthought.com',
    maintainer='Sean Ross-Ross',
    maintainer_email='enthought-dev@enthought.com',
    url='http://srossross.github.com/Meta',
    
    classifiers=[c.strip() for c in """\
        Development Status :: 5 - Production/Stable
        Intended Audience :: Developers
        License :: OSI Approved :: BSD License
        Operating System :: MacOS
        Operating System :: Microsoft :: Windows
        Operating System :: OS Independent
        Operating System :: POSIX
        Operating System :: Unix
        Programming Language :: Python
        Topic :: Scientific/Engineering
        Topic :: Software Development
        Topic :: Software Development :: Libraries
        """.splitlines() if len(c.strip()) > 0],
    description='Byte-code and ast programming tools',
    long_description=long_description,
    include_package_data=True,
    license='BSD',
    packages=find_packages(),
    platforms=["Windows", "Linux", "Mac OS-X", "Unix", "Solaris"],
    entry_points={
                    'console_scripts': [
                                        'depyc = meta.scripts.depyc:main',
                                        ],
                    }

)
