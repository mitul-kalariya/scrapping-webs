# Mainichi Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://mainichi.jp/ website and the tech stacks used are
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
# To fetch all the article links from today's date only

from crwmainichi import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://mainichi.jp/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwmainichi import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://mainichi.jp/articles/20230330/k00/00m/040/076000c?cx_testId=122&cx_testVariant=cx_2&cx_artPos=0#cxrecs_s"
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
