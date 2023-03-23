import json
from datetime import datetime
from scrapy.http import Response


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
    initial_url = "https://www.leparisien.fr/arc/outboundfeeds/news-sitemap-index/?from=0&outputType=xml&_website="\
        "leparisien"
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
