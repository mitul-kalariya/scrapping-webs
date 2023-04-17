from setuptools import setup, find_packages

setup(
    name='crwcp24',
    author='Newton',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'scrapy',
        'pillow',
        'selenium',
        'beautifulsoup4',
        'webdriver_manager'
    ],
)
