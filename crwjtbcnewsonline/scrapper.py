# TODO: Change the path below
from crwsueddeutsche import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
