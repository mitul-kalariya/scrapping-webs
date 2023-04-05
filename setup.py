from setuptools import find_packages, setup

setup(
    name="crwhk01",
    author="Newton",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "scrapy",
        "selenium",
        "webdriver-manager",
    ],
)
