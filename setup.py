from setuptools import setup, find_packages

setup(
    name='crwlepoint',  # TODO: <-- Change name here as per the folder
    author='Newton',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
    ],
)
