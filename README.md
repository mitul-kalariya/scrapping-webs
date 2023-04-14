# CP24 Scraping
This is the scrapping project to scrap news from different website.


#### Setup and execution instructions: - 

This repo contains the code to scrap all sitemaps (if available) and articles from https://www.cp24.com/ website and the Tech stacks used are
- Python 3.10
- Scrapy
- Selenium


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

from crwcp24 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.cp24.com/"
    },
    proxies=proxies
)

data = crawler.crawl()
```
```
# To fetch all the article links from selected dates
from crwcp24 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.cp24.com/",
        "since": "2023-04-01",
        "until: "2023-04-15"
    },
    proxies=proxies
)

data = crawler.crawl()
```

*Note:* We have made video extraction optional which we can controll by extra parameter i.e enable_selenium. By default it is False.
```
#  To fetch the specific article details
from crwcp24 import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": 'https://www.cp24.com/news/police-in-india-identify-family-who-died-crossing-illegally-into-u-s-from-akwesasne-1.6341143'
    },
    proxies=proxies,
    enable_selenium=False
)

data = crawler.crawl()
```

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`

### Use of Selenium

Yes, we used selenium to fetch video url. To manage the selenium we are using [Web-Driver](https://pypi.org/project/webdriver-manager/) package and we are using `ChromeDriverManager`.