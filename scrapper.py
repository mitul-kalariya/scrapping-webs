from crwbbcnews import Crawler

crawler = Crawler(query={"type": "link_feed"})
links = crawler.crawl()

for link in links[:3]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    breakpoint()
    print(data)
    print("----------------------------------------------------")

print(data)
