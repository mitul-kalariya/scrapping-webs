# TODO: Change the path below
from crwtokyokeizai import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)