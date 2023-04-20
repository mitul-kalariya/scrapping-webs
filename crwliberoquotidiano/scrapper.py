# TODO: Change the path below
from crwliberoquotidiano import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
