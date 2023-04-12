from crwtfinews import Crawler

# crawler = Crawler(query={"type": "sitemap"})
# links = crawler.crawl()
# for link in links[:2]:
#     article = Crawler(query={"type": "article", "link": link["link"]})
#     data = article.crawl()
#     print(data)
#     print("----------------------------------------------------")

# print(data)

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.tf1info.fr/",
        "since": "2023-02-20",
        "until": "2023-02-22"
    }
)

data = crawler.crawl()

print(data)