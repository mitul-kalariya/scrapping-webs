# Newton Scrapping

## About The Project

This is the scrapping project to scrap news from different website.

#### Python setup

- `virtulenv venv` and `source venv/bin/activate`
- `pip install -r requirements.txt`
- command to crawl articles `scrapy crawl indianexpress -a category=articles`
- command to crawl articles with date `scrapy crawl indianexpress -a category=articles -a start_date=2023-03-06 -a end_date=2023-03-06`
- command to crawl on articles on one date `scrapy crawl indianexpress -a category=articles -a start_date=2023-03-06`
- command to crawl sitemap without date `scrapy crawl indianexpress -a category=sitemap`
- command to crawl sitemap with date `scrapy crawl indianexpress -a category=sitemap -a start_date=2023-03-06 -a end_date=2023-03-06`
- command to crawl on sitemap on one date `scrapy crawl indianexpress -a category=sitemap -a start_date=2023-03-06`


*Note:* Make sure to enter the virtual env before running.

<p align="right">(<a href="#top">back to top</a>)</p>
