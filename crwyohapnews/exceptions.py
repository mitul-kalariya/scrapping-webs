# Exception
# exceptions.py

class InvalidInputException(Exception):
    pass


class InputMissingException(Exception):
    pass


class LinkFeedScrappingException(Exception):
    pass


class ArticleScrappingException(Exception):
    pass


class ExportOutputFileException(Exception):
    pass


class ParseFunctionFailedException(Exception):
    pass


class ProxyConnectionException(Exception):
    pass


class CrawlerClosingException(Exception):
    """Rise when getting error while closing crawler status code"""
    pass
