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
- `pip install -r requirements.txt ` 
*Note:* Make sure to enter the virtual env before running.


## Indian Express

#### Sitemap file available: - Yes 


#### Command to fetch sitemap: - 

- command to crawl on sitemap from specific date range
- `scrapy crawl indian_express-a type=sitemap-a start_date=2023-03-06 -a end_date=2023-03-10`
- command to crawl sitemap for today’s date
- `scrapy crawl indian_express -a type=sitemap` 


#### Commands to fetch Articles: - 

- command to crawl wanted article
- `scrapy crawl indian_express -a type=article -a url={{Article-URL}}` 

## Test Cases
We have used Python's in-built module `unittest`. We have covered mainly two test cases.
1. For Sitemap article links crawler
2. For Article data Crawler

Run below command to run the test cases.
- `python -m coverage run -m unittest`

Run below command to chec the test cases coverage.
- `python -m coverage html`

