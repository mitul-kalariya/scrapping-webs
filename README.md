# Newton Scrapping
This is the scrapping project to scrap news from different website.


#### Setup and execution instructions: - 

This repo contains the code to scrap all sitemaps (if available) and articles from {website name} website and the Tech stacks used are
- Python 3.10
- Scrapy


#### Environment Setup 

- Create Virtual Environment using Python3 and activate environment.
- `python3 -m venv venv`
- `source venv/bin/activate`
- Install Requirements using requirements.txt file available in a main directory.
- `pip install -r requirements.txt

### Package Information
A package is already created inside the `dist` directory and if you want to create a new package after any changes then run the below command
```
python setup.py sdist
```

### Installation

Use the command `pip install <path_to_package>`. for example `pip install dist/crwmediapart-0.1.tar.gz`

### Usage

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.
```
from crwmediapart import Crawler

# For Article
crawler = Crawler(query={"type": "article", "link": https://example.com/articles/test.html"})
data = crawler.crawl()

# For Sitemap
crawler = Crawler(query={"type": "sitemap", "domain": "https://example.com", "since": "2022-03-01", "until": "2022-03-26"})
data = crawler.crawl()

# For Link Feed
crawler = Crawler(query={"type": "link_feed"})
data = crawler.crawl()
```
The `query` argument will be changed as per the type like `sitemap`, `article`, and `link_feed`. More details are added in the code documentation.

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`
