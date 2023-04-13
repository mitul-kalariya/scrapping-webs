from crwardnews import Crawler

# crawler = Crawler(query={"type": "sitemap"})
# links = crawler.crawl()

links = [
    {
    "link": "https://www.tagesschau.de/ausland/thaci-kosovo-101.html"
    },
    {
    "link": "https://www.tagesschau.de/wirtschaft/konjunktur/wti-brent-opec-russland-oelpreis-101.html"
    },
    {
    "link": "https://www.tagesschau.de/ausland/europa/finnland-konservative-wahlsieg-105.html"
    },
    {
        "link": "https://www.tagesschau.de/kommentar/cannabis-legalisierung-115.html"
    }
]
for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)