from crwnhkorjp import Crawler

# Wrong Proxy Shared by Henry
proxies = {
    "proxyIp": "166.81.191.33",
    "proxyPort": "4616",
    "proxyUsername": "stt_proxy_user55",
    "proxyPassword": "xw34$21dOoww_",
    "proxyTimeout": 5
}

# Proxy shared earlier
proxies = {
    "proxyIp": "104.239.117.168",
    "proxyPort": "3199",
    "proxyUsername": "daniel_morgan-57n47",
    "proxyPassword": "IgNyTnWKr5",
}
# Working Proxy created by us
proxies = {
    "proxyIp": "3.20.87.239",
    "proxyPort": "3128",
    "proxyUsername": "testuser",
    "proxyPassword": "testpass",
}

try:
    crawler = Crawler(query={"type": "sitemap", "domain": ""}, proxies=proxies)
    links = crawler.crawl()
except Exception as e:
    print("here", e)

links = [
    {
        "link": "https://www3.nhk.or.jp/news/html/20230403/k10014027131000.html"
    }
]

print(f"Total {len(links)} found..")
for link in links[:2]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print("----------------------------------------------------")


# http://username:password@some_proxy_server:port
# stt_proxy_user55:xw34$21dOoww_@166.81.191.33:1616
