import json
from datetime import datetime
from scrapy.http import Response


def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (FranceTvInfo): The FranceTvInfo spider instance.
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
    initial_url = "https://www.francetvinfo.fr/sitemap_index.xml"
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
    mapper = {"FRA": "France", "fr": "French"}
    article_data = {}
    article_data["title"] = response.css('h1.c-title ::text').get()
    article_data["section"] = response.css('li.breadcrumb__item a::text').getall()
    selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()
    article_data["json_data"] = [json.loads(data) for data in selector]
    language = response.css("html::attr(lang)").get()
    article_data["language"] = mapper.get(language)
    article_data["country"] = mapper.get("FRA")
    return article_data


def set_article_dict(self, response: Response, article_data: dict) -> dict:
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

    json_data_0 = article_data.get("json_data")[0]
    article = {
        'raw_response': {
            "content_type": response.headers.get("Content-Type").decode("utf-8"),
            "content": response.text,
        },
        "parsed_json": {
            "main":
                article_data.get("json_data")

        },
        "parsed_data": {
            "language": article_data["language"],
            "country": article_data["country"],
            "description": [json_data_0['description']],
            "modified_at": [json_data_0['dateModified']],
            "published_at": [json_data_0['datePublished']],
            "publisher": [{'@type': json_data_0['Publisher']['@type'],
                           'name': json_data_0['Publisher']['name'],
                           'logo': {'@type': json_data_0['Publisher']['logo']['@type'],
                                    'url': json_data_0['Publisher']['logo']['url'],
                                    'width': {'@type': "Distance",
                                              "name": f"{json_data_0['Publisher']['logo']['width']['value']} Px"},
                                    'height': {'@type': "Distance",
                                               'name': f"{json_data_0['Publisher']['logo']['height']['value']} Px"}}}],
            "text": [json_data_0['articleBody']],
            "thumbnail_image": [json_data_0["image"][0]['url']],  # need to look it
            "title": [article_data.get('title')],
            "images": [{'link': image['url']} for image in json_data_0['image']],
            "section": [article_data.get('section')[2].strip()],
            "tags": json_data_0['keywords'].split(',')
        }
    }
    try:
        article["parsed_data"]["author"] = [
            {"@type": json_data_0['author']['@type'], "name": json_data_0['author']['name'],
             "url": json_data_0['author']['url']}]
    except Exception as e:
        self.logger.exception(f"Error in {set_article_dict.__name__} - {e}")
        article["parsed_data"]["author"] = [
            {"@type": json_data_0['author'][0]['@type'], "name": json_data_0['author'][0]['name'],
             "url": json_data_0['author'][0]['url']}]
    return article