## TimesNowNews Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [times now news](https://www.timesnownews.com/) website and the Tech stacks used are:-
-  Python 3.10
-  Scrapy 

### Environment Setup 
 
Create Virtual Environment using Python3 and activate environment. 
```bash
python3 -m venv venv
```
```bash
source venv/bin/activate
```

### Install required dependencies

Install requirements using requirements.txt file available in main
```bash
pip install -r requirements.txt
```

### Sitemap file available:- Yes

### Command to fetch Sitemap:-
-  Command to crawl on sitemap from specific date range
```bash
scrapy crawl times_now_news -a type=sitemap -a start_date=2023-03-11 -a end_date=2023-03-13
```
    
-  Command to crawl sitemap for today’s date  
```bash
scrapy crawl times_now_news -a type=sitemap
```
    
### Command to fetch Articles:-
[timesnownews_article_url](https://www.timesnownews.com/business-economy/markets/top-stocks-to-buy-sell-today-14th-march-2023-tech-mahindra-rbl-bank-lt-finance-holdings-check-share-price-target-stop-loss-and-other-details-kunal-bothras-cracker-stocks-article-98626158)
```bash
scrapy crawl spider_name -a type=article url=timesnownews_article_url
```

## Test Cases
We have used Python's in-built module `unittest`.
We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data CrawlerRun below command to run the test cases.
- `python -m unittest`
