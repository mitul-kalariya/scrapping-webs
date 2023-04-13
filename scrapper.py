# TODO: Change the path below
from crwyonhapnews import Crawler

proxy = {
    "proxyIp":"168.81.229.17",
    "proxyPort":"3199",
    "proxyPassword":"IgNyTnWKr5",
    "proxyUsername":"daniel_morgan-57n47"
}
# crawler = Crawler(query={"type": "sitemap"})
# data = crawler.crawl()
crawler = Crawler(
    query={
        "type": "article",
        "link": "https://m-en.yna.co.kr/view/AEN20230405003651315"
    },
    proxies=proxy
)

data = crawler.crawl()
print(data)
