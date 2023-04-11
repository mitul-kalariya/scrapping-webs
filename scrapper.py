from crwmediapart import Crawler

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://www.mediapart.fr",
        "since": "2023-02-25",
        "until": "2023-03-26"
    },
)
data = crawler.crawl()

print(data)
