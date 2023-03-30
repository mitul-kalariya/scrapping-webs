#TODO: Change the path below
from crwlemonde import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
