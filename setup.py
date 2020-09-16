#!/usr/bin/env python
# -*- coding: utf-8 -*-


from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst', encoding='utf-8') as history_file:
    history = history_file.read()

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.read()


setup(
    name='awsm',
    description="Automated Water Supply Model",
    author="USDA ARS Northwest Watershed Research Center",
    author_email='snow@ars.usda.gov',
    url='https://github.com/USDA-ARS-NWRC/awsm',
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires='>3.5',
    packages=find_packages(include=['awsm', 'awsm.*']),
    include_package_data=True,
    package_data={
        'awsm': [
            './framework/CoreConfig.ini',
            './framework/recipes.ini'
        ]
    },
    scripts=[
        './scripts/awsm',
        './scripts/wyhr',
        './scripts/plot_csv',
        './scripts/clean_awsm',
        './scripts/awsm_daily',
        './scripts/awsm_daily_airflow'
    ],
    install_requires=requirements,
    license="CC0 1.0",
    zip_safe=False,
    keywords='awsm',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    test_suite='tests',
    use_scm_version={
        'local_scheme': 'node-and-date',
    },
    setup_requires=[
        'setuptools_scm'
    ],
)
