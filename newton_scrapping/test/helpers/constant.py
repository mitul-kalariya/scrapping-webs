"""list of article/sitemap URLs for testing"""

# Update below dictionary to add or remove new articles to test
TEST_ARTICLES = [
    {
        "url": "https://www.mediapart.fr/journal/politique/250323/francois-ruffin-la-masse-le-nombre-c-est-le-seul-chemin-pour-la-victoire",
        "test_data_path": "newton_scrapping/test/data/test_article_1.json"
    },
    {
        "url": "https://www.mediapart.fr/journal/economie-et-social/270323/arnaud-rousseau-un-poids-lourd-de-l-agrobusiness-pour-diriger-la-fnsea",
        "test_data_path": "newton_scrapping/test/data/test_article_2.json"
    },
    # {
    #     "url": "https://indianexpress.com/article/sports/cricket/david-still-has-a-burning-desire-to-open-the-batting-for-australia-candice-warner-8512422/",
    #     "test_data_path": "newton_scrapping/test/data/test_article_3.json"
    # }
]

SITEMAP_URL = "https://www.mediapart.fr/sitemap_index.xml"
