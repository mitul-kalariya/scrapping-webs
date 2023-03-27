# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import scrapy
from scrapy import Item, Field


class NewtonScrappingItem(scrapy.Item):
    # define the fields for your item here like:
    pass


class ArticleData(Item):
    raw_response = Field()
    parsed_json = Field()
    parsed_data = Field()


class ArticleRawResponse(Item):
    content_type = Field()
    content = Field()


class ArticleRawParsedJson(Item):
    main = Field()
    misc = Field()
    ImageGallery = Field()
    VideoObject = Field()
    other = Field()
