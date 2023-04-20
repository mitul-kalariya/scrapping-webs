# Exception
# exceptions.py

class InvalidInputException(Exception):
    """Raise when invalid input is given"""

    pass


class InputMissingException(Exception):
    """Raise when any of the required input is missing"""

    # Use InputMissingException(f"Please enter {input_param}")
    pass


class LinkFeedScrappingException(Exception):
    """Raise when exception arise while fetching Link Feed"""

    # Use SitemapScrappingException(f"Error occurred while fetching sitemap:- {str(e)}")
    pass



class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use ArticleScrappingException(f"Error occurred while fetching article details:- {str(e)}")
    pass


class ExportOutputFileException(Exception):
    """Raise when exception arise while exporting output file"""

    # Use ExportOutputFileException(f"Error occurred while exporting file:- {str(e)}")
    pass



class ParseFunctionFailedException(Exception):
    """An exception raised when parse function fails."""

    # use ParseFunctionFailedException(f"Error occured in parse function: {e}")
    pass

class ProxyConnectionException(Exception):
    """Rise when getting 403 or 407 status code"""
    pass
