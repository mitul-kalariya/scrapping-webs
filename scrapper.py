from crwnationalpost import Crawler

proxy = {
    "proxyIp":"168.81.229.17",
    "proxyPort":"3199",
    "proxyPassword":"IgNyTnWKr5",
    "proxyUsername":"daniel_morgan-57n47"
}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'

# crawler = Crawler(
#     query={
#         "type": "article",
#         "link": "https://nationalpost.com/pmn/sports-pmn/hockey-sports-pmn/markstrom-reigns-over-kings-as-flames-win-2-1"
#     },
#     proxies=proxy
# )

# data = crawler.crawl()

# print(data)

crawler = Crawler(
    query={
        "type": "sitemap",
        "domain": "https://nationalpost.com/",
        "since": "2023-02-28",
        "until": "2023-02-28"
    },
    proxies=proxy
)
data = crawler.crawl()

for link in data[:2]:
    print(link)
    print("----------------------------------------------------")