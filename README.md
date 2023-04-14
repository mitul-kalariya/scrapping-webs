# Bastille Post Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.bastillepost.com/ website and the tech stacks used are
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

*Note:* Here we are getting data from link_feed.

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.

```
# To fetch all the article links from today's date only

from crwbastillepost import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://www.bastillepost.com/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwbastillepost import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.bastillepost.com/hongkong/article/12545585-%e6%b8%af%e7%94%a2%e7%a3%81%e5%8a%9b%e5%85%b1%e6%8c%af%e6%88%90%e5%83%8f%e7%a0%94%e7%99%bc%e6%89%8e%e6%a0%b9%e5%a4%a7%e5%9f%94-%e9%ab%98%e7%ab%af%e7%94%9f%e7%94%a2%e5%8a%a9%e6%b8%af%e6%8e%a8%e5%8b%95"
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
