from crwam730 import Crawler


proxies = {
    "proxyIp": "168.81.229.17",
    "proxyPort": "3199",
    "proxyUsername": "",
    "proxyPassword": "IgNyTnWKr5"
}

links = [
    {
        "link": "https://www.am730.com.hk/本地/內地女捲冒廉電騙案-來港開戶串謀洗黑錢判囚1年/371169"
    },
]

for link in links:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
