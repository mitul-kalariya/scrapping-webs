from crwfrancetv import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()

for link in links[:5]:
    breakpoint()
    article = Crawler(query={"type": "article", "link": link["link"]}, enable_selenium=False)
    data = article.crawl()
    print(data)
