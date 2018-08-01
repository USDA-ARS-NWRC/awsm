#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
from setuptools import setup, find_packages
import os
import subprocess
from subprocess import check_output, PIPE

#Grab and write the gitVersion from 'git describe'.
gitVersion = ''
gitPath = ''

# get git describe if in git repository
print('Fetching most recent git tags')
if os.path.exists('./.git'):
	try:
		# if we are in a git repo, fetch most recent tags
		check_output(["git fetch --tags"], shell=True)
	except Exception as e:
		print(e)
		print('Unable to fetch most recent tags')

	try:
		ls_proc = check_output(["git describe --tags"], shell=True, universal_newlines=True)
		gitVersion = ls_proc
		print('Checking most recent version')
	except Exception as e:
		print('Unable to get git tag and hash')
# if not in git repo
else:
	print('Not in git repository')
	gitVersion = ''

# get current working directory to define git path
gitPath = os.getcwd()

# git untracked file to store version and path
fname = os.path.abspath(os.path.expanduser('./awsm/utils/gitinfo.py'))

with open(fname,'w') as f:
	nchars = len(gitVersion) - 1
	f.write("__gitPath__='{0}'\n".format(gitPath))
	f.write("__gitVersion__='{0}'\n".format(gitVersion[:nchars]))
	f.close()

with open('README.md',encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst', encoding='utf-8') as history_file:
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
    version='0.6.1',
    description="Automated Water Supply Forecasting",
    long_description=readme + '\n\n' + history,
    author="Micah Sandusky",
    author_email='micah.sandusky@ars.usda.gov',
    url='https://github.com/USDA-ARS-NWRC/AWSM',
    packages=['awsm',
			  'awsm.convertFiles',
			  'awsm.interface',
			  'awsm.framework',
              'awsm.knn',
			  'awsm.utils',
			  'awsm.reporting'
			  ],


    include_package_data=True,
    package_data={'awsm':['./framework/CoreConfig.ini',
				  './framework/recipes.ini']},
    scripts=['./scripts/awsm','./scripts/wyhr',
			 './scripts/plot_csv', './scripts/plot_ipw'],
    install_requires=requirements,
    license="CC0 1.0",
    zip_safe=False,
    keywords='awsm',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU GPL-3.0',
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
