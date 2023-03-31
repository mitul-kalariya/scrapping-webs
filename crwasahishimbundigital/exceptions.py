# Exception
# exceptions.py
class InvalidDateException(Exception):
    """Raise when invalid date is passed"""

    pass


class InvalidArgumentException(Exception):
    """Raise when invalid date is passed"""

    pass


class InputMissingException(Exception):
    """Raise when any of the required input is missing"""

    pass


class SitemapScrappingException(Exception):
    """Raise when exception arise while fetching sitemap"""

    pass


class SitemapArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use SitemapArticleScrappingException(f"Error occurred while fetching article details from sitemap:- {str(e)}")
    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use ArticleScrappingException(f"Error occurred while fetching article details:- {str(e)}")
    pass


class ExportOutputFileException(Exception):
    """Raise when exception arise while exporting output file"""

    # Use ExportOutputFileException(f"Error occurred while exporting file:- {str(e)}")
    pass


class ServiceUnavailableException(Exception):
    """Rise when getting 403, 406, 429 or >500 status code"""

    # Use ServiceUnavailableException(f"Service Unavailable for {website_name} and {url}
    # with {response.status_code} and {response.reason}")
    pass


class URLNotFoundException(Exception):
    """Rise when getting 404 status code"""

    # Use URLNotFoundException(f"Given {url} not found for website {website_name}
    # with status code{response.status_code}")
    pass