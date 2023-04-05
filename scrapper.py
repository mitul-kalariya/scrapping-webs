from crwzdfnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()

for link in links[:2]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")

print(data)
