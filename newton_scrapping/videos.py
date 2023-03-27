from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time


def get_video(self, url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    try:
        time.sleep(10)
        disagree_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@class="didomi-components-button didomi-button didomi-disagree-button didomi-button-standard standard-button"]'))
        )
        disagree_button.click()
        time.sleep(5)
        play_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@role="presentation"]'))
        )
        play_button.click()
        time.sleep(2)
        play_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="ftv-magneto--btn ftv-magneto--focusable-item"]'))
        )
        play_button.click()
        time.sleep(5)
        iframe_text = driver.find_element(By.XPATH, '//div[@role="dialog"]//div[@role="presentation"]/span')
        text = iframe_text.text
        text = text.split('//')
        text = text[1].split('"')[0]
        driver.close()
        return f"https://{text}"

    except Exception as e:
        self.logger.exception(f"Error in {get_video.__name__} -> {e}")
