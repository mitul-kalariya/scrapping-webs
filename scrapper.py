from crwtfinews import Crawler

proxies = {
    "proxyIp": "168.81.229.17",
    "proxyPort": "3199",
    "proxyUsername": "",
    "proxyPassword": "IgNyTnWKr5"
}


# crawler = Crawler(query={"type": "link_feed"})
# links = crawler.crawl()
# print(links)
links = [
    {
    "link": "https://www.tf1info.fr/culture/video-le-jeu-prefere-des-francais-fete-ses-75-ans-cinq-anecdotes-a-caser-sur-le-scrabble-2253994.html"
    }
]
for link in links[:2]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")


