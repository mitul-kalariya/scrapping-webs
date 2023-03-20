""" General functions """
from datetime import timedelta, datetime


ERROR_MESSAGES = {
    "MISSING_REQUIRED_FIELD": "'{}' field is required.",
    "VALID_DATE_RANGE": "Please provide valid date range.",
    "BETWEEN_DATE_RANGE": "Please provide date range between 30 days",
    "NOT_REQUIRED_FIELD": "Invalid argument. {}",
}


def sitemap_validations(scrape_start_date, scrape_end_date, article_url):
    """Validate the sitemap arguments"""
    current_date = None
    if scrape_start_date and scrape_end_date:
        validate_arg("VALID_DATE_RANGE", not scrape_start_date > scrape_end_date)
        validate_arg(
            "BETWEEN_DATE_RANGE",
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            "MISSING_REQUIRED_FIELD",
            not (scrape_start_date or scrape_end_date),
            "start_date and end_date",
        )
        current_date = datetime.now().date()

    validate_arg(
        "NOT_REQUIRED_FIELD", not article_url, "url is not required for sitemap."
    )

    return current_date


def article_validations(article_url, scrape_start_date, scrape_end_date):
    """Validate the article arguments"""
    validate_arg("MISSING_REQUIRED_FIELD", article_url, "url")
    validate_arg(
        "NOT_REQUIRED_FIELD",
        not (scrape_start_date or scrape_end_date),
        "start_date and end_date argument is not required for article.",
    )


def date_range(start_date, end_date):
    """
    return range of all date between given date
    if not end_date then take start_date as end date
    """
    try:
        for date in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(date)

    except Exception as exception:
        print(exception)
        # log(
        #     f"Error occured while generating date range. {str(exception)}",
        #     level=logging.ERROR,
        # )


def validate_arg(param_name, param_value, custom_msg=None):
    """common function for validate argument"""
    if not param_value:
        raise ValueError(ERROR_MESSAGES[param_name].format(custom_msg or param_name))


def based_on_type(scrape_type, scrape_start_date, scrape_end_date, url):
    """check scrape type and based on scrape type pass to the vaildation function,
    after validation return required values."""
    if scrape_type == "article":
        article_validations(url, scrape_start_date, scrape_end_date)
        return None, None
    if scrape_type == "sitemap":
        scrape_start_date = scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return scrape_start_date, date_range_lst

    return validate_arg("MISSING_REQUIRED_FIELD", None, "type")
