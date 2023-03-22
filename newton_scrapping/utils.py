import os
import json
import logging


def create_log_file_config_and_logger():

    # Setting the threshold of logger to DEBUGlogging.basicConfig(
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return logging.getLogger()

def make_directories_for_links_and_article():

    links_path = "Links"
    article_path = "Article"

    if not os.path.exists(links_path):
        os.makedirs(links_path)
    if not os.path.exists(article_path):
        os.makedirs(article_path)
    
    return links_path, article_path

class InvalidDateRange(Exception):
    pass

def validations_for_start_date_and_end_date(self, start_date, end_date, today_date):
    
    if start_date and not end_date:
        self.import_logs["error"] = "end_date must be specified if start_date is provided"

    if not start_date and end_date:
        self.import_logs["error"] = "start_date must be specified if end_date is provided"

    if start_date and end_date and start_date > end_date:
        self.import_logs["error"] = "start_date should not be later than end_date"

    if start_date and end_date and start_date == end_date:
        self.import_logs["error"] = "start_date and end_date must not be the same"

    if start_date and end_date and start_date > today_date:
        self.import_logs["error"] = "start_date must not greater than today date"

    if start_date and end_date and end_date > today_date:
        self.import_logs["error"] = "end_date must not greater than today date"

    return self.import_logs

def get_main(self, response):
    breakpoint()
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:
        data = []
        misc = response.css('script[type="application/ld+json"]::text').getall()
        for block in misc:
            data.append(json.loads(block))
        return data
    except BaseException as e:
        self.logger.error(f"{e}")
        print(f"Error while getting main: {e}")