from datetime import datetime
from collections.abc import Generator
from typing import Any

from .timesnow import TimesNow
from scrapy.http import Response


def check_cmd_args(self: TimesNow, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.

    Args:
        self (TimesNow): The TimesNow spider instance.
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
    self.logger.info(
        f'======================== {check_cmd_args.__name__} will start working ===============================')
    initial_url = "https://www.timesnownews.com/staticsitemap/timesnow/sitemap-index.xml"
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

    elif self.type == "articles" and self.url is not None:
        self.start_urls.append(self.url)

    elif self.type == "articles" and self.url is None:
        raise ValueError("type articles must be used with url")

    else:
        raise ValueError("type should be articles or sitemap")


def request_today_or_range_date(self: TimesNow, site_map_url: list, response: Response) -> Generator:
    # if not today's date the start date and end date will be available
    # if not self.today_date:
    self.logger.info(
        '======================== start to follow url ===============================')
    try:
        for url in site_map_url:
            # , mod_date):
            # _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
            # if not today's date the start date and end date will be available
            # if not self.today_date:
            #     if _date.month == self.start_date.month or _date.month == self.end_date.month:
            #         yield response.follow(url, callback=self.parse_sitemap)
            # else it will fetch only today's date as start date and date is none
            # else:
            #     if _date.month == self.today_date.month:
            self.logger.info(
                '======================== start to follow url ===============================')
            yield response.follow(url, callback=self.parse_sitemap)
    except Exception as e:
        self.logger.exception(f"Error in {request_today_or_range_date.__name__}:- {e}")

    # else it will fetch only today's date as start date and date is none
    # else:
    #     try:
    #         for url, date in zip(site_map_url, mod_date):
    #             _date = datetime.strptime(date.split("T")[0], '%Y-%m-%d')
    #             if _date.month == self.today_date.month:
    #                 yield response.follow(url, callback=self.parse_sitemap)
    #     except Exception as e:
    #         self.logger.exception(f"Error in {request_today_or_range_date.__name__}:- {e}")
