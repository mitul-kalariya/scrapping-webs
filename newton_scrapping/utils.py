# Utility/helper functions
# utils.py

import os
import json
from datetime import datetime


def validate():
    # This function to validate the input args
    # like start_Date, end_date, type and raise error if require else return nothing
    # This should be called from __init__ method of Spider
    pass


def get_raw_response(response):
    # This should return the raw response in proper format
    pass


def get_parsed_json(response):
    # This should extract the main and misc object and return in proper format
    pass


def get_parsed_data(response):
    # This should return the properly formatted parsed_data object
    pass


# below method should be called from get_parsed_data function


def get_author(response):
    pass


def get_publisher(response):
    pass


def get_description(response):
    pass


def get_modified_at(response):
    pass


def get_published_at(response):
    pass


def get_publisher(response):
    pass


def get_text(response):
    pass


def get_thumbnail_image(response):
    pass


def get_title(response):
    pass


def get_images(response):
    pass


def get_section(response):
    pass


def get_embed_video_link(response):
    pass


def export_data_to_json_file(scrape_type: str, file_data: str, file_name: str) -> None:
    """
    Export data to json file
    Args:
        scrape_type: Name of the scrape type
        file_data: file data
        file_name: Name of the file which contain data
    Raises:
        ValueError if not provided
    Returns:
        Values of parameters
    """
    folder_structure = ""
    if scrape_type == "sitemap":
        folder_structure = "Links"
        filename = (
            f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )
    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )
    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)
    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)
