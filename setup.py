from setuptools import setup, find_packages

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

setup(
    name="ascar-dql",
    version="0.1",
    packages=find_packages(),

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['matplotlib',
                      'numpy',
                      'pyzmq',
                      'python-daemon',
                      'Sphinx',
                      'sphinx_rtd_theme'],

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'hello': ['*.msg'],
    },

    # metadata for upload to PyPI
    author='Yan Li',
    author_email='yanli@tuneup.ai',
    description="ASCAR Using Deep Reinforcement Learning",
    license="BSD",
    keywords="machine-learning",
    url="https://ascar.io/",   # project home page, if any

    # could also include long_description, download_url, classifiers, etc.
)