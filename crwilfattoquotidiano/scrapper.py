# TODO: Change the path below
from crwilfattoquotidiano import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
