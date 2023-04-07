import scrapy
import requests
import json


class STDNewsSpider(scrapy.Spider):
    name = "stdnews"
    start_urls = ["https://std.stheadline.com/realtime/get_more_instant_news"]

    def __init__(self, *args, **kwargs):
        super(STDNewsSpider, self).__init__(*args, **kwargs)
        self.request_headers = {
            "authority": "std.stheadline.com",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "dnt": "1",
            "origin": "https://std.stheadline.com",
            "referer": "https://std.stheadline.com/realtime/%E5%8D%B3%E6%99%82",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }
        self.articles = []

    def parse(self, response):
        self.get_sitemap(response)
        yield self.articles

    def get_sitemap(self, response):
        today_flag = True
        page_counter = 1
        while today_flag == True:
            response_json = (requests.request(
                "POST",
                "https://std.stheadline.com/realtime/get_more_instant_news",
                headers=self.request_headers,
                data="page="+str(page_counter),
            )).json()
            article_list = response_json.get("data")
            for article_data in article_list:
                if "\u65e5\u524d" in article_data.get("publish_datetime"):
                    today_flag = False
                    break
                self.articles.append(
                    {
                        "link":article_data.get("articleLink"),
                        "title":article_data.get("title").get("tc"),
                    }
                )
            page_counter+=1