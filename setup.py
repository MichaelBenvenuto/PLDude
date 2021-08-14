from os import name
from sys import version
import setuptools

setuptools.setup(
    name='pldude',
    version='0.9.0',
    author='Michael Benvenuto',
    entry_points={
        'console_scripts':[
            'pldude=pldude.__main__:main'
        ]
    }
)