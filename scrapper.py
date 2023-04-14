# from crwntv import Crawler

# crawler = Crawler(query={"type": "link_feed"})
# links = crawler.crawl()

# for link in links[:10]:
#     article = Crawler(query={"type": "article", "link": link["link"]})
#     data = article.crawl()
#     print(data)
#     print(type(data))


import os

import json

# Opening JSON file
f = open(
    "/home/mitul/_03_ Dev&git/production_newton_scrapping/newton-scrapping/Links/n_tv-sitemap-2023-04-14_18-00-21.json"
)

# returns JSON object as
# a dictionary
data = json.load(f)

# Iterating through the json
# list
for i in data:
    print(i.get("link"))
    os.system(f"scrapy crawl n_tv -a type=article -a url={i.get('link')}")
# Closing file
f.close()