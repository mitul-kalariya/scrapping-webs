## Leparisien Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [Leparisien](https://www.leparisien.fr/) website and the Tech stacks used are:-
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
scrapy crawl le_parisien -a type=sitemap -a start_date=2023-03-11 -a end_date=2023-03-13
```
    
-  Command to crawl sitemap for today’s date  
```bash
scrapy crawl le_parisien -a type=sitemap
```
    
### Command to fetch Articles:-
[Laprisien_article_url](https://www.leparisien.fr/sports/football/pas-appele-en-equipe-de-france-depuis-2020-houssem-aouar-va-representer-lalgerie-15-03-2023-BLJ2OJSGFVADTNP4DHYWESB3HQ.php)
```bash
scrapy crawl le_parisien -a type=article url=timesnownews_article_url
```
