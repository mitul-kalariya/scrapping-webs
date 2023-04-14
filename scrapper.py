from crwzeitnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()

for link in links[:1]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    breakpoint()
    print(data)
    print("----------------------------------------------------")

print(data)
