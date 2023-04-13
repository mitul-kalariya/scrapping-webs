from setuptools import setup, find_packages

setup(
    name='crwglobalnews',
    author='Newton',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'pillow',
        'lxml',
    ],
)
