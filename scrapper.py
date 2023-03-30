from crw20minutesonline import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()
counter = 0

for link in links:
    crawler = Crawler(query={"type": "article", "url": link['link']})
    article = crawler.crawl()
    with open(f"article_{counter}.json", "w") as file:
        file.write(json.dumps(article, indent=4))
