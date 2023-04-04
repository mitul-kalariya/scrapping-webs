# Oriental Daily News (CH) Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from "https://orientaldaily.on.cc/" website and the tech stacks used are
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

from crworientaldaily import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://orientaldaily.on.cc/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crworientaldaily import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://orientaldaily.on.cc/content/%E8%A6%81%E6%B8%AF%E8%A6%81%E8%81%9E/odn-20230329-0329_00174_002/%E5%88%86%E4%BA%AB%E5%88%A9%E6%BD%A4%E6%AD%B8%E5%85%A5%E7%AE%97%E5%BC%8F--%E6%96%B0%E5%88%B6%E5%B0%91%E9%80%BE%E5%84%84%E5%84%AA%E6%83%A0/"
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
