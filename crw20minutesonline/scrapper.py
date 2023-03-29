#TODO: Change the path below
from crw20minutesonline import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
