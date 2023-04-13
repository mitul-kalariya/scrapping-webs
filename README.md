# STD Stheadline Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://std.stheadline.com/ website and the tech stacks used are
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

from crwstdnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://std.stheadline.com/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwstdnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://std.stheadline.com/realtime/article/1918576/%E5%8D%B3%E6%99%82-%E6%B8%AF%E8%81%9E-%E9%83%BD%E5%A4%A7%E7%A0%94%E7%A9%B6%E5%9C%98%E9%9A%8A%E9%96%8B%E7%99%BC%E6%96%B0%E6%BC%94%E7%AE%97%E6%B3%95-%E6%8F%90%E5%8D%87%E7%84%A1%E7%B7%9A%E7%B6%B2%E7%B5%A1%E6%95%88%E8%83%BD"
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
