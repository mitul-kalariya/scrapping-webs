# ZEIT Scrapping

#### Setup and execution instructions: -

This repo contains the code to scrap all article links and articles from https://www.zeit.de/ website and the tech stacks used are

- Python 3.10
- Scrapy 2.8.0
- requests 2.28.2
- selenium-wire 5.1.0
- selenium 4.8.3
- webdriver-manager 3.8.5

#### Environment Setup

- Create a Virtual Environment using Python3 and activate the environment.
- `python3 -m venv venv`
- `source venv/bin/activate`

_Note:_ Make sure to activate the virtual environment before executing code or installing the package.

> ```Important Note:``` We are generating **cookies & request headers** using seleniumwire and webdriver manager for all pages requests, Hence  we have not included ***enable_selenium*** flag

### Note:- To scrape this website we have to set cookie in headers and that procedure takes time initially since we are using selenium to do that.

### Installation

Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.

### Usage

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.

_Note:_ Here we are getting data from sitemap.

```


# To fetch all the article links

from crwzeitnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.zeit.de/",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
# To fetch all the article links from today's date only

from crwzeitnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.zeit.de/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwzeitnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.zeit.de/kultur/musik/2023-04/rat-saw-god-wednesday-album-indierock"
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
