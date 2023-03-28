from crwzdfnews import Crawler

# crawler = Crawler(query={"type": "sitemap"})
crawler = Crawler(query={"type": "article", "link": "https://www.zdf.de/nachrichten/politik/ukraine-russland-konflikt-blog-100.html"})
data = crawler.crawl()

print(data)
