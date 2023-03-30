#TODO: Change the path below
from crwhk01 import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
