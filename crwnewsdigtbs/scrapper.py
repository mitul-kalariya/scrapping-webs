#TODO: Change the path below
from crwnewsdigtbs import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
