from setuptools import setup, find_packages

setup(
    name='crwbfmtv',
    author='Newton',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'selenium',
        'webdriver-manager',
        'beautifulsoup4',
    ],
)
