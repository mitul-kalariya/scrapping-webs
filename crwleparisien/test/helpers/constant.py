"""list of article/sitemap URLs for testing"""

#TODO:Update below dictionary to add or remove new articles to test
TEST_ARTICLES = [
    {
        "url": "https://www.leparisien.fr/faits-divers/il-a-gagne-ma-confiance-nordine-s-lescroc-des-coeurs-qui-a-soutire-au-moins-43000-euros-a-ses-victimes-28-03-2023-YQV22USD2NBWLEOTOQEOVLIGFQ.php",
        "test_data_path": "crwleparisien/test/data/test_article_1.json"
    },
    {
        "url": "https://www.leparisien.fr/environnement/insectes-avec-le-rechauffement-climatique-les-pollinisateurs-ont-le-bourdon-29-03-2023-OXR4DH7M2BD3VBOLBTCILKZJ7Y.php",
        "test_data_path": "crwleparisien/test/data/test_article_2.json"
    },
    {
        "url": "https://www.leparisien.fr/sports/football/rennes-fin-de-saison-pour-adrien-truffert-vers-un-forfait-pour-leuro-espoirs-29-03-2023-EDKP5MPZXBAHBC22JUZ37ZGZSE.php",
        "test_data_path": "crwleparisien/test/data/test_article_3.json"
    }
]

SITEMAP_URL = "https://www.leparisien.fr/arc/outboundfeeds/news-sitemap/?from=0&outputType=xml&_website=leparisien"
