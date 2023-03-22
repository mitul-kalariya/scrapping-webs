import json
from datetime import datetime
from scrapy.http import Response


def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (ZeitDeNews): The ZeitDeNews spider instance.
        start_date (str): The start date for the sitemap spider in the format YYYY-MM-DD.
        end_date (str): The end date for the sitemap spider in the format YYYY-MM-DD.

    Raises:
        ValueError: If the type is not "articles" or "sitemap".
        ValueError: If the type is "sitemap" and either start_date or end_date is missing.
        ValueError: If the type is "sitemap" and the time range is more than 30 days.
        ValueError: If the type is "articles" and the URL is missing.

    Returns:
        None.

       Note:
           This function assumes that the class instance variable `start_urls` is already initialized as an empty list.
       """
    initial_url = "https://www.linternaute.com/sitemap/"
    if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("Enter start_date and end_date for maximum 30 days.")
        else:
            self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
        self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
        raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

    elif self.type == "article" and self.url is not None:
        self.start_urls.append(self.url)

    elif self.type == "article" and self.url is None:
        raise ValueError("type articles must be used with url")

    else:
        raise ValueError("type should be articles or sitemap")


def get_article_data(response: Response) -> dict:
    """
       Extracts relevant data from the response of the given URL
       :param response: The response object obtained from a HTTP request to the URL
       :return: A dictionary containing relevant article data.
       """
    article_data = {}
    selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
    article_data["json_data"] = [json.loads(data) for data in selector]

    json_data_misc = response.xpath('//script[@type="application/json"]/text()').getall()
    article_data['json_data_misc'] = [json.loads(data) for data in json_data_misc]

    article_data["title"] =  response.css('div.entry h1::text').get()
    article_data["sub_title"] = response.css('p.app_entry_lead::text').get()
    desc = response.css('p.app_entry_diapo__description font font::text').getall()
    if len(desc)!=0:
        article_data['description'] = desc
    else:
        article_data['description'] = response.css('p.app_entry_diapo__description::text').getall()

    cat =response.css('nav.ccmcss_breadcrumb font font::text').getall()
    if cat:
        article_data["category"] = cat
    else:
        article_data['category'] = response.css('nav.ccmcss_breadcrumb div a span::text').getall()
    
    return article_data


def set_article_dict(response: Response, article_data: dict) -> dict:
    """
      Takes in a `Response` object and a dictionary containing article data, and returns a dictionary
      containing the article information in a standardized format.

      Args:
          response (requests.Response): A `Response` object containing the raw HTTP response data.
          article_data (dict): A dictionary containing the extracted article data.

      Returns:
          dict: A dictionary containing the article information in a standardized format. The
          dictionary contains three main sections: `raw_response`, `parsed_json`, and `parsed_data`.
          The `raw_response` section contains the raw response data from the HTTP request, while
          the `parsed_json` section contains the parsed JSON-LD data extracted from the article.
          The `parsed_data` section contains the article information extracted from the raw HTML data.
      """
    
    if article_data.get("json_data")[0][0].get('author')==None:
        index=1
    else:
        index=0   
    
    article = {
        'raw_response': {
            "content_type": response.headers.get("Content-Type").decode("utf-8"),
            "content": response.text,
        },
        "parsed_json": {
            "main": article_data.get("json_data"),
            "misc": article_data.get("json_data_misc")
        },
        "parsed_data": {
            "author": [{"@type":article_data.get("json_data")[0][index].get('author').get("@type"), "name":article_data.get("json_data")[0][index].get('author').get("name"), "url":article_data.get("json_data")[0][index].get('author').get("url")}],
            "description": [article_data.get("json_data")[0][index].get('description')],
            "modified_at": [article_data.get("json_data")[0][index]['dateModified']],
            "published_at": [article_data.get("json_data")[0][index]['datePublished']],
            # "retrieved_at": [datetime.today().strftime("%Y-%m-%d")],
            "publisher": [{'@type': article_data.get("json_data")[0][index]['publisher']['logo']['@type'],
                          'url': article_data.get("json_data")[0][index]['publisher']['logo']['url'],
                          'width': {'@type': "Distance",
                                    "name": str(article_data.get("json_data")[0][index]['publisher']['logo']['width']) + " Px"},
                          'height': {'@type': "Distance",
                                     'name': str(
                                         article_data.get("json_data")[0][index]['publisher']['logo']['width']) + " Px"}}],
            "text": [article_data.get("json_data")[0][index].get("articleBody")],
            "thumbnail_image": [article_data.get("img_url")],  # need to look it
            "title": article_data.get("title"),
            "images": [{"link": article_data.get("json_data")[0][index].get('image').get('url'), "caption": article_data.get('json_data')[0][index].get('image').get('url')}],
            "country": ["France"]
        }
    }
    
    if article["parsed_data"]['description'] == ['']:
        article["parsed_data"]['description'] = ["".join(article_data.get('description'))]
        article["parsed_data"]['text'] = ["".join(article_data.get('description'))]
    else:
        article["section"] = article_data.get("category")    

    return article

# def request_today_or_range_date(self: TimesNow, site_map_url: list, response: Response) -> Generator:
#     # if not today's date the start date and end date will be available
#     # if not self.today_date:
#     self.logger.info(
#         '======================== start to follow url ===============================')
#     try:
#         for url in site_map_url:
#             # , mod_date):
#             # _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
#             # if not today's date the start date and end date will be available
#             # if not self.today_date:
#             #     if _date.month == self.start_date.month or _date.month == self.end_date.month:
#             #         yield response.follow(url, callback=self.parse_sitemap)
#             # else it will fetch only today's date as start date and date is none
#             # else:
#             #     if _date.month == self.today_date.month:
#             self.logger.info(
#                 '======================== start to follow url ===============================')
#             yield response.follow(url, callback=self.parse_sitemap)
#     except Exception as e:
#         self.logger.exception(f"Error in {request_today_or_range_date.__name__}:- {e}")
#
#     # else it will fetch only today's date as start date and date is none
#     # else:
#     #     try:
#     #         for url, date in zip(site_map_url, mod_date):
#     #             _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
#     #             if _date.month == self.today_date.month:
#     #                 yield response.follow(url, callback=self.parse_sitemap)
#     #     except Exception as e:
#     #         self.logger.exception(f"Error in {request_today_or_range_date.__name__}:- {e}")
