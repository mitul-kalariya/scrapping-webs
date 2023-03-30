# HK01 News Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.hk01.com/ website and the tech stacks used are
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
```
# To fetch all the article links

from crwhk01 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.hk01.com/",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
    proxies=proxies
)

data = crawler.crawl()
```
```
# To fetch all the article links from today's date only

from crwhk01 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.hk01.com/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwhk01 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.hk01.com/%E6%94%BF%E6%83%85/882169/%E9%A6%96%E8%B8%8F%E8%B6%B3%E6%94%BF%E7%B8%BD-%E9%84%AD%E9%9B%81%E9%9B%84%E5%BB%A3%E6%9D%B1%E8%A9%B1%E5%A0%B1%E5%91%8A-%E6%9D%8E%E5%AE%B6%E8%B6%85%E8%AC%9B%E6%99%AE%E9%80%9A%E8%A9%B1%E9%AB%94%E7%8F%BE-%E4%B8%80%E5%9C%8B%E5%85%A9%E5%88%B6"
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
