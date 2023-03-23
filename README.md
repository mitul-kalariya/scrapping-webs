## France-Info-TV Scraper

This repo contains the code to scrap all sitemaps (if available) and articles from [France-tv-info](https://www.francetvinfo.fr/) website and the Tech stacks used are:-
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
scrapy crawl francetv-info -a type=sitemap -a start_date=2023-03-11 -a end_date=2023-03-13
```
    
-  Command to crawl sitemap for today’s date  
```bash
scrapy crawl francetv-info -a type=sitemap
```
    
### Command to fetch Articles:-
[francetvinfo_article_url](https://www.francetvinfo.fr/economie/retraite/reforme-des-retraites/retraites-face-aux-elus-de-la-majorite-emmanuel-macron-a-voulu-tracer-les-perspectives-des-annees-qui-viennent-selon-le-depute-renaissance-benjamin-haddad_5724728.html)
```bash
scrapy crawl francetv-info -a type=article url=timesnownews_article_url
```
