from setuptools import setup, find_packages

setup(
    name='crwmediapart',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'pillow',
    ],
)
