# ARD News Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.tagesschau.de website and the tech stacks used are
- Python 3.10
- Scrapy 2.8.0
- W3lib 2.1.1


### Environment Setup 
 
Create a Virtual Environment using Python3 and activate the environment. 
```bash
python3 -m venv venv
```
```bash
source venv/bin/activate
```

*Note:* Make sure to activate the virtual environment before executing code or installing the package.

### Installation

Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.
### Usage

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.
```
# To fetch all the article links

from crwardnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.tagesschau.de",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
    proxies=proxies
)

data = crawler.crawl()
```
```
# To fetch all the article links from today's date only

from crwardnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.tagesschau.de"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwardnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.tagesschau.de/ausland/europa/finnland-konservative-wahlsieg-105.html"
    },
    proxies=proxies
)

data = crawler.crawl()

# For Sitemap
crawler = Crawler(query={"type": "sitemap", "domain": "https://example.com", "since": "2022-03-01", "until": "2022-03-26"})
data = crawler.crawl()

# For Link Feed
crawler = Crawler(query={"type": "link_feed"})
data = crawler.crawl()
```

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`
