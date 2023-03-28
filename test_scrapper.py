from crwmediapart import Crawler

crawler = Crawler(query={"type": "sitemap"})
crawler = Crawler(query={"type": "article", "link": "https://www.mediapart.fr/journal/economie-et-social/280323/hassan-retraite-de-81-ans-mange-parfois-avec-5-francs-par-jour"})
data = crawler.crawl()

print(data)
