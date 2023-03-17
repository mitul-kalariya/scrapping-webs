## Economist Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [Economist](https://www.economist.com) website and the Tech stacks used are:-
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
scrapy crawl economist_canada -a type=sitemap -a start_date=2023-03-11 -a end_date=2023-03-13
```
    
-  Command to crawl sitemap for today’s date  
```bash
scrapy crawl economist_canada -a type=sitemap
```
    
### Command to fetch Articles:-
[Economist_article_url](https://www.economist.com/podcasts/2023/01/02/the-world-is-entering-a-new-nuclear-age-an-old-fear-returns)
```bash
scrapy crawl economist_canada -a type=article url=timesnownews_article_url
```
