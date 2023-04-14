# ZDF Scrapping

#### Setup and execution instructions: - 

This repo contains the code to scrap all article links and articles from https://www.zdf.de/ website and the tech stacks used are
- Python 3.10  
- Scrapy 2.8.0
- selenium 4.8.3
- webdriver-manager 3.8.5
- Pillow 9.5.0


#### Environment Setup

- Create a Virtual Environment using Python3 and activate the environment.
- `python3 -m venv venv`
- `source venv/bin/activate`

*Note:* Make sure to activate the virtual environment before executing code or installing the package.

### Installation

Use the command `python setup.py install`. This will install the whole package in your virtual environment and you can use the following code and get started.
### Use of Selenium

Yes, we used selenium to fetch video URLs. To manage the selenium we are using [Web-Driver](https://pypi.org/project/webdriver-manager/) package and we are using `ChromeDriverManager`.

### Usage

*Note:* Here we are getting data from the sitemap.

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.
```
# To fetch all the article links

from crwzdfnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.zdf.de/",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
    proxies=proxies
)

data = crawler.crawl()
```
```
# To fetch all the article links from today's date only

from crwzdfnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.zdf.de/"
    },
    proxies=proxies
)

data = crawler.crawl()
```

```
#  To fetch the specific article details

from crwzdfnews import Crawler

proxies = {
    "proxyIp": "168.92.23.26", # just added dummy IP
    "proxyPort": "yourport", # example 3199
    "proxyUsername": "yourusername",
    "proxyPassword": "yourpassword"
}

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://www.zdf.de/nachrichten/briefing/ukraine-netanjahu-gellinek-zdfheute-update-100.html"
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