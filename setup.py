# coding=utf-8

import os

from galaxycat import __version__
from setuptools import setup, find_packages

current_dir = os.path.dirname(__file__)
LONG_DESC = open(os.path.join(current_dir, "README.md")).read()
with open(os.path.join(current_dir, "requirements.txt")) as f:
    requirements = f.read().splitlines()

setup(
    name=u"galaxycat",
    version=__version__,
    description="A galaxy online catalog server",
    long_description=LONG_DESC,
    author="Julien Seiler",
    author_email="julien.seiler@gmail.com",
    license="GNU GENERAL PUBLIC LICENSE v2",
    url="",
    zip_safe=False,
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        'Natural Language :: English',
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
    ],
    packages=find_packages(),
    package_dir={'galaxycat': 'galaxycat'},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'galaxycat = galaxycat.cli:cli'

        ]
    }
)
