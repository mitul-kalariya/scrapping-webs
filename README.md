# Newton Scrapping
This is the scrapping project to scrap news from different website.


#### Setup and execution instructions: - 

This repo contains the code to scrap all sitemaps and articles from sueddeutsche website and the Tech stacks used are
- Python 3.10
- Scrapy


#### Environment Setup 

- Create Virtual Environment using Python3 and activate environment.
- `python3 -m venv venv`
- `source venv/bin/activate`
- Install Requirements using requirements.txt file available in a main directory.
- `pip install -r requirements.txt `


#### Sitemap file available: - Yes (used archiv)


#### Command to fetch URL using Archiv: - 

- command to crawl on sitemap from specific date range
- `scrapy crawl sueddeutsche -a type=sitemap -a start_date=2023-03-06 -a end_date=2023-03-10`
- command to crawl sitemap for today’s date
- `scrapy crawl sueddeutsche -a type=sitemap`


#### Commands to fetch Articles: - 

- command to crawl wanted article
- `scrapy crawl sueddeutsche -a type=article -a url={{Article-URL}}`

*Note:* Make sure to enter the virtual env before running.
