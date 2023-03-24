import json
from datetime import datetime
from scrapy.http import Response

from .exceptions import (
    InputMissingException,
    InvalidDateException,
    InvalidArgumentException,
)
from newton_scrapping.constant import (
    SITEMAP_URL,
    DATE_FORMAT
)

def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (LeParisien): The ZeitDeNews spider instance.
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
    # initial_url = "https://www.timesnownews.com/staticsitemap/timesnow/sitemap-index.xml"

    validate_type(self)

    if self.type == "sitemap":
        handle_sitemap_type(self, start_date, end_date, SITEMAP_URL)

    elif self.type == "article":
        handle_article_type(self)


def add_start_url(self, url):
    self.start_urls.append(url)


def set_date_range(self, start_date, end_date):
    self.start_date = datetime.strptime(start_date, DATE_FORMAT)
    self.end_date = datetime.strptime(end_date, DATE_FORMAT)


def validate_date_range(self):
    if self.start_date > self.end_date:
        raise InvalidDateException("start_date must be less then end_date")
    if (self.end_date - self.start_date).days > 30:
        raise InvalidDateException("Enter start_date and end_date for maximum 30 days.")


def validate_type(self):
    if self.type not in ["article", "sitemap"]:
        raise InvalidArgumentException("type should be articles or sitemap")


def handle_sitemap_type(self, start_date, end_date, initial_url):
    if self.end_date is not None and self.start_date is not None:
        set_date_range(self, start_date, end_date)
        validate_date_range(self)
        add_start_url(self, initial_url)

    elif self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime(DATE_FORMAT)
        self.today_date = datetime.strptime(today_time, DATE_FORMAT)
        add_start_url(self, initial_url)

    elif self.end_date is not None or self.start_date is not None:
        raise InvalidArgumentException("to use type sitemap give only type sitemap or with start date and end date")


def handle_article_type(self):
    if self.url is not None:
        add_start_url(self, self.url)
    else:
        raise InputMissingException("type articles must be used with url")


def get_article_data(response: Response) -> dict:
    """
       Extracts relevant data from the response of the given URL
       :param response: The response object obtained from a HTTP request to the URL
       :return: A dictionary containing relevant article data.
       """
    mapper = {"FRA": "France", "fr-FR": "French"}
    article_data = {}
    article_data["title"] = response.css('header.article_header > h1::text').getall()
    article_data["img_url"] = response.css("div.width_full >figure > div.pos_rel > img::attr('src')").getall()
    article_data["img_caption"] = response.css('div.width_full >figure > figcaption > span::text').getall()
    article_data["article_author_url"] = response.css('a.author_link::attr(href)').getall()
    article_data["video_link"] = response.css('iframe.dailymotion-player::attr(src)').getall()
    article_data["text"] = response.css('section.content > p::text').getall()
    article_data["category"] = response.css('div.breadcrumb > a::text').getall()

    json_data = "".join(response.css('script[type="application/ld+json"]::text').getall())

    json_data = json.loads(json_data)
    article_data['json_data'] = json_data
    json_misc_data = response.css('script[type="application/json"]::text').getall()
    article_data['json_misc_data'] = [json.loads(misc) for misc in json_misc_data]
    language = response.css("html::attr(lang)").get()
    article_data["language"] = mapper.get(language)
    article_data["country"] = mapper.get("FRA")
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
    json_data = article_data.get('json_data')
    article = {
        'raw_response': {
            "content_type": response.headers.get("Content-Type").decode("utf-8"),
            "content": response.text,
        },
        "parsed_json": {
            "main": article_data.get('json_data'),
            "misc": article_data.get('json_misc_data')
        },

        "parsed_data": {
            "language": article_data["language"],
            "country": article_data["country"],
            "author": [
                {
                    "@type": json_data[1]['author'][0]["@type"],
                    "name": json_data[1]['author'][0]["name"],
                }
            ],
            "description": [json_data[1]['description']],
            "modified_at": [json_data[1]['dateModified']],
            "published_at": [json_data[1]['datePublished']],

            "publisher": [
                {
                    '@type': json_data[1]['publisher']['@type'],
                    'name': json_data[1]['publisher']['name'],
                    'logo': {
                        '@type': json_data[1]['publisher']['logo']['@type'],
                        'url': json_data[1]['publisher']['logo']['url'],
                        'width': {
                            '@type': "Distance",
                            "name": str(json_data[1]['publisher']['logo']['width']) + " Px"},
                        'height': {
                            '@type': "Distance",
                            'name': str(json_data[1]['publisher']['logo']['height']) + " Px"}}}],

            "text": ["".join(article_data.get('text'))],
            "thumbnail_image": [json_data[2]["url"] + article_data.get('img_url')[0][1:]],  # need to look it
            "title": article_data.get('title'),
            "images": [{'link': json_data[2]["url"] + article_data.get('img_url')[0][1:], 'caption': \
                article_data.get('img_caption')[0]}],

            "section": "".join(article_data.get('category')).split(","),
            "tags": json_data[1]["keywords"]
        }
    }

    if article_data.get('article_author_url'):
        article['parsed_data']['author'][0]['url'] = json_data[2]["url"] + article_data.get('article_author_url')[0][1:]

    if article_data.get("video_link"):
        article['parsed_data']['embed_video_link'] = [article_data.get("video_link")]
    return article
