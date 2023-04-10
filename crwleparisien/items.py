# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html


import scrapy
from scrapy import Item, Field
from itemloaders.processors import TakeFirst


class NewtonScrappingItem(scrapy.Item):
    # define the fields for your item here like:
    pass


class ArticleData(Item):
    raw_response = Field(output_processor=TakeFirst())
    parsed_json = Field(output_processor=TakeFirst())
    parsed_data = Field(output_processor=TakeFirst())


class ArticleRawResponse(Item):
    content_type = Field()
    content = Field()


class ArticleRawParsedJson(Item):
    main = Field(output_processor=TakeFirst())
    misc = Field()
    ImageGallery = Field()
    imageObjects = Field()
    videoObjects = Field()
    other = Field()
