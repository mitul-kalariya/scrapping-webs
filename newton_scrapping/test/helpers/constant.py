"""list of article/sitemap URLs for testing"""

# Update below dictionary to add or remove new articles to test
TEST_ARTICLES = [
    {
        "url": "https://www.bfmtv.com/international/amerique-nord/canada/canada-un-pick-up-fauche-des-pietons-dans-une-ville-du-quebec-au-moins-deux-morts-et-plusieurs-blesses_AD-202303130820.html",
        "test_data_path": "newton_scrapping/test/data/test_article_1.json"
    },
    {
        "url": "https://www.bfmtv.com/politique/elysee/reforme-des-retraites-emmanuel-macron-estime-avoir-une-majorite-solide-a-l-assemblee-nationale_AN-202303130628.html",
        "test_data_path": "newton_scrapping/test/data/test_article_2.json"
    },
    {
        "url": "https://www.bfmtv.com/tech/bons-plans/cette-chaise-gaming-est-a-un-prix-qui-va-vous-convaincre_AB-202303110033.html",
        "test_data_path": "newton_scrapping/test/data/test_article_3.json"
    }
]

SITEMAP_URL = "https://www.bfmtv.com/sitemap_index_arbo_contenu.xml"
