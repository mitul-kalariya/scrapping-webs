from crwctvnews import Crawler

crawler = Crawler(query={"type": "sitemap", "since": "2023-04-06", "until": "2023-04-06"})
data = crawler.crawl()

print(data)
