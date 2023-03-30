import logging

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(filename='selenium.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')


class Selenium:
    def __init__(self):
        self.service = Service(executable_path=ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service)

    def visit(self, url):
        self.driver.get(url)

    def get_text(self):
        # try:
        #     self.text = WebDriverWait(self.driver, 2).until(
        #         EC.visibility_of_element_located((By.CSS_SELECTOR, "h6.descContainer > pre"))
        #     )
        # except Exception as e:
        #     logging.exception(f"error in {self.get_text.__name__} - {e}")
        #     print(e)
        return self.driver.find_element(By.CSS_SELECTOR, 'h6.descContainer > pre').text

    def get_title(self):
        return self.driver.find_element(By.CSS_SELECTOR, 'div.newsEntryContainer h1').text

    def get_category(self):
        print(f">>>>>>>>  {list(map(lambda x: x.text, self.driver.find_elements(By.CSS_SELECTOR, 'div.breadcrumbContainer a h5 font font')))}")
        return self.driver.find_elements(By.CSS_SELECTOR, 'div.breadcrumbContainer a h5 font font')

    def close(self):
        self.driver.close()
