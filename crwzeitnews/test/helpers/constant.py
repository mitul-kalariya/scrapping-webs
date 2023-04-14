"""list of article/sitemap URLs for testing"""

TEST_ARTICLES = [
    {
        "url": "https://www.zeit.de/video/2023-04/6324065533112/un-sicherheitsrat-russische-kinderrechtsbeauftragte-sorgt-fuer-eklat-bei-un-sitzung",  # video article
        "test_data_path": "crwzeitnews/test/data/test_article_1.json",
    },
    {
        "url": "https://www.zeit.de/kultur/musik/2023-04/rat-saw-god-wednesday-album-indierock",  # article with yt videos
        "test_data_path": "crwzeitnews/test/data/test_article_2.json",
    },
    {
        "url": "https://www.zeit.de/arbeit/2023-04/arbeitszeitbetrug-angestellte-kuendigung",
        "test_data_path": "crwzeitnews/test/data/test_article_3.json",
    },
]

SITEMAP_URL = "https://www.zeit.de/gsitemaps/index.xml"
