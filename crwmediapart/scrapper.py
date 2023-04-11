# TODO: Change the path below
from crwsueddeutsche import Crawler

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "{BASE_URL}",
        "since": "2023-04-01",
        "until": "2023-04-11"
    },
)
data = crawler.crawl()

print(data)
