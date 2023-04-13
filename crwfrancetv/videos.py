import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_video(self, url):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(3)
        play_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@role="presentation"]'))
        )
        play_button.click()
        time.sleep(6)
        play_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="ftv-magneto--btn ftv-magneto--focusable-item"]'))
        )
        play_button.click()
        time.sleep(2)
        iframe_text = driver.find_element(By.XPATH, '//div[@role="dialog"]//div[@role="presentation"]/span')
        var = iframe_text.get_attribute('innerHTML')
        video_id = var.split('//embed.francetv.fr/')[1].split('"')[0]
        text = f"https://embed.francetv.fr/{video_id}"

        driver.close()
        return text
    except Exception as exception:
        self.log(
            f"Error while fetching video url:- {str(exception)}",
            level=logging.ERROR,
        )
