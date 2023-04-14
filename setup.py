from setuptools import setup, find_packages

setup(
    name='crwrepublictv',
    author='Newton',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'requests',
    ],
)
