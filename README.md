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
        "type": "sitemap",
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
        "link": "https://std.stheadline.com/realtime/article/1918005/%E5%8D%B3%E6%99%82-%E5%9C%8B%E9%9A%9B-%E6%96%B0%E5%8A%A0%E5%9D%A1%E6%96%B0%E5%86%A0%E7%A2%BA%E8%A8%BA%E6%BF%80%E5%A2%9E-%E5%B0%88%E5%AE%B6%E6%8C%87%E6%88%96%E8%88%87%E6%96%B0%E8%AE%8A%E7%A8%AE%E6%AF%92%E6%A0%AA%E6%9C%89%E9%97%9C"
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
