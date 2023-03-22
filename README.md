## Linternaute Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [Linternaute news](https://www.linternaute.com/) website and the Tech stacks used are:-
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
scrapy crawl linternaute -a type=sitemap -a start_date=2023-03-11 -a end_date=2023-03-13
```
    
-  Command to crawl sitemap for today’s date  
```bash
scrapy crawl linternaute -a type=sitemap
```
    
### Command to fetch Articles:-
[cp24_article_url](https://www.linternaute.com/cinema/biographie/1774942-marcel-marceau-biographie-courte-dates-citations/)
```bash
scrapy crawl linternaute -a type=article url=timesnownews_article_url
```

