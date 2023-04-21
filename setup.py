from setuptools import setup, find_packages

setup(
    name='crwmbcnews',
    author='Newton',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        "json5"
    ],
)
