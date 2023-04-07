# Times Now News Scrapping
Setup and execution instructions: -
This repo contains the code to scrap all article links and articles from https://www.timesnownews.com/ website and the tech stacks used are
- Python 3.10
- Scrapy
## Environment Setup
Create a Virtual Environment using Python3 and activate the environment.
```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```
Note: Make sure to activate the virtual environment before executing code or installing the package.

## Installation
Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.

## Usage
You can use the `Crawler` class and its `crawl` method to crawl the data. Quick example as shown below.
Getting data for more then one month
```
# To fetch all the article links
from crwtimesnownews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.timesnownews.com/",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
# To fetch all the article links from today's date only
from crwtimesnownews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.timesnownews.com/"
    },
    proxies=proxies
)

data = crawler.crawl()
```
```
#  To fetch the specific article details

from crwtimesnownews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.timesnownews.com/india/to-look-like-bhindranwale-amritpal-went-to-georgia-for-cosmetic-surgery-report-article-99311886"
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
