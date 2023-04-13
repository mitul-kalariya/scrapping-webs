from setuptools import setup, find_packages

setup(
    name='crwterra',
    author='Newton',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'selenium',
        'webdriver-manager'
    ],
)
