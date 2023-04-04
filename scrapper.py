from crwhuffpost import Crawler

crawler = Crawler(query={"type": "article", "link": "https://www.huffingtonpost.fr/divertissement/article/pekin-express-l-elimination-de-ce-binome-et-un-handicap-inutile-ont-degoute-les-internautes-spoilers_215967.html"})
data = crawler.crawl()

print(data)
