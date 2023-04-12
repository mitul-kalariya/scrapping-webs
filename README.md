# Leparisien Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.leparisien.fr/ website and the tech stacks used are
- Python 3.10
- Scrapy


#### Environment Setup

- Create a Virtual Environment using Python3 and activate the environment.
- `python3 -m venv venv`
- `source venv/bin/activate`

*Note:* Make sure to activate the virtual environment before executing code or installing the package.

### Installation

Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.
### Usage

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.
Article data available for 3-4 days only including today's date

```
# To fetch all the article links from today's date only

from crwleparisien import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://www.leparisien.fr/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwleparisien import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.leparisien.fr/info-paris-ile-de-france-oise/transports/transports-en-ile-de-france-les-perturbations-du-week-end-de-paques-du-8-au-10-avril-07-04-2023-5LVGUDMJFZEGVBRJH4V3MIVYYU.php"
    },
    proxies=proxies
)

data = crawler.crawl()
```

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`
