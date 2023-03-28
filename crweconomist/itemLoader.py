from itemloaders.processors import (
    TakeFirst,
    MapCompose,
    Identity
)
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from crweconomist.constant import (
    TYPE,
    LIST_OF_PARSED_JSON_OBJECT,
    NEWS_ARTICLE,
    IMAGE_GALLERY,
    VIDEO_OBJECT
)


def other_filter(values):
    lst_other = []
    if values.get(TYPE) not in LIST_OF_PARSED_JSON_OBJECT:
        lst_other.append(values)
    return lst_other


def main_filter(values):
    if values.get(TYPE) == NEWS_ARTICLE:
        return values


def image_gallery_filter(values):
    if values.get(TYPE) == IMAGE_GALLERY:
        return values


def video_object_filter(values):
    if values.get(TYPE) == VIDEO_OBJECT:
        return values


class ArticleDataLoader(ItemLoader):
    default_output_processor = TakeFirst()


class ArticleRawResponseLoader(ItemLoader):
    default_output_processor = TakeFirst()
    content_type_in = MapCompose(remove_tags)


class ArticleRawParsedJsonLoader(ItemLoader):
    default_output_processor = TakeFirst()
    main_in = MapCompose(main_filter)
    ImageGallery_in = MapCompose(image_gallery_filter)
    VideoObject_in = MapCompose(video_object_filter)
    other_in = MapCompose(other_filter)
    other_out = Identity()
