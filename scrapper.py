from crwtfinews import Crawler

# crawler = Crawler(query={"type": "sitemap"})
crawler = Crawler(query={"type": "article", "link": "https://www.tf1info.fr/international/etats-unis-un-grand-jury-a-new-york-a-vote-pour-inculper-au-penal-ex-president-donald-trump-dans-affaire-stormy-daniels-actrice-porno-2252626.html"})
data = crawler.crawl()

print(data)
