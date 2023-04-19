# MBN News Online Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.mbn.co.kr/news/ website and the tech stacks used are
- Python 3.10
- Scrapy 2.8.0
- selenium 4.8.3
- webdriver_manager 3.8.5


#### Environment Setup

- Create a Virtual Environment using Python3 and activate the environment.
- `python3 -m venv venv`
- `source venv/bin/activate`

*Note:* Make sure to activate the virtual environment before executing code or installing the package.

### Installation

Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.
Sitemap data is available only for 3 days Including today's date.
### Usage
```
# To fetch all the article links from today's date only

from crwmbnnewsonline import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "link_feed",
        "domain": "https://www.mbn.co.kr/news/"
    },
    proxies=proxies
)

data = crawler.crawl()
```
Note: We have made image extraction optional which we can control by extra parameter i.e enable_selenium. By default it is False.


```
#  To scrap data with selenium while scrapping article

from crwmbnnewsonline import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.mbn.co.kr/news/entertain/4917683"
    },
    proxies=proxies
    enable_selenium=True
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

Yes, we used selenium to fetch Images from the website. To manage the selenium we are using webdriver_manager(https://pypi.org/project/webdriver-manager/) package and we are using `ChromeDriverManager`.