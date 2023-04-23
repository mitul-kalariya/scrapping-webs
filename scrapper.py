# TODO: Change the path below
import json
from crwyonhapnews import Crawler

proxy = {
    "proxyIp":"168.81.229.17",
    "proxyPort":"3199",
    "proxyPassword":"IgNyTnWKr5",
    "proxyUsername":"daniel_morgan-57n47"
}
# crawler = Crawler(query={"type": "sitemap"})
# data = crawler.crawl()
# crawler = Crawler(
#     query={
#         "type": "article",
#         "link": "https://m-en.yna.co.kr/view/AEN20230405003651315"
#     },
#     proxies=proxy
# )

# data = crawler.crawl()
# print(data)

# crawler = Crawler(
#     query={
#         "type": "link_feed",
#         "domain": "https://en.yna.co.kr/",
#         # "since": "2023-02-25",
#         "until": "2023-03-26"
#     },
#     proxies=proxy
# )

# data = crawler.crawl()
# print(data)

TEST_ARTICLES = [
    {
        "url": "https://en.yna.co.kr/view/AEN20230419006200320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419006100320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419005600315"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419005500325"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419005400315"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419005100315"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419002800320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419005000320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419003851320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419004700315"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419003800320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419004200315"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419004400320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419002000320"
    },
    {
        "url": "https://en.yna.co.kr/view/AEN20230419000952325"
    }
]

count = 1
for link in TEST_ARTICLES:
    article = Crawler(query={"type": "article", "link": link["url"]})
    data = article.crawl()
    json_object = json.dumps(data, indent=4)
    with open(f"crwyonhapnews/test/data/test_article_{count}.json", "w") as f:
        f.write(json_object)
    print(data)
    count+=1
    print("----------------------------------------------------")