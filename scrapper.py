from crwzdfnews import Crawler

# crawler = Crawler(query={"type": "sitemap"})
crawler = Crawler(query={"type": "article", "link": "https://www.zdf.de/nachrichten/video/panorama-usa-amoklauf-grundschule-nashville-100.html"})
data = crawler.crawl()

print(data)
