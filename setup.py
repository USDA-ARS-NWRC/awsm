#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    # TODO: put package requirements here
]

setup_requirements = [
    # TODO(micahsandusky5): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='awsm',
    version='0.1.0',
    description="Automated Water Supply Forecasting",
    long_description=readme + '\n\n' + history,
    author="Micah Sandusky",
    author_email='micah.sandusky@ars.usda.gov',
    url='https://github.com/micahsandusky5/awsm',
    packages=['awsm',
			  'awsm.convertFiles',
			  'awsm.interface',
			  'awsm.framework',
              'awsm.knn'
			  ],


    include_package_data=True,
    package_data={'awsm':['./framework/CoreConfig.ini']},
    scripts=['./scripts/awsm'],
    install_requires=requirements,
    license="GPL-3.0",
    zip_safe=False,
    keywords='awsm',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
