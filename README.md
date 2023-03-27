## CP24 Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [cp24 news](https://www.cp24.com) website and the Tech stacks used are:-
-  Python 3.10
-  Scrapy 
-  Selenium
- Beautiful Soup

### Environment Setup 
 
Create Virtual Environment using Python3 and activate environment. 
```bash
python3 -m venv venv
```
```bash
source venv/bin/activate
```

### Sitemap file available:- Yes

### Sitemap file available:- Yes

### Package Information
A package is already created inside the `dist` directory and if you want to create a new package after any changes then run the below command
```
python setup.py sdist
```

### Installation

Use the command `pip install <path_to_package>`. for example `pip install dist/crwcp24-0.1.tar.gz`

### Usage

You can use the `Crawler` class and its `crawl` method to crawl the data.
Quick example as shown below.
```
from crwcp24 import Crawler

crawler = Crawler(query={"type": "article", "link": https://example.com/articles/test.html"})
data = crawler.crawl()
```
The `query` argument will be changed as per the type like `sitemap`, `article`, and `link_feed`. More details are added in the code documentation.

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`
