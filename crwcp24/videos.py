from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def get_video(self, url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    try:
        textarea = driver.find_element(By.XPATH, '//*[@id="jw-settings-submenu-sharing"]/div/div[2]/textarea')
        value = textarea.get_attribute("value")

        iframe_string = value
        soup = BeautifulSoup(iframe_string, 'html.parser')
        video_url = soup.iframe.get("src")
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, '//video[@class="jw-video jw-reset"]'))
        )
    except Exception as e:
        self.logger.exception(f"Error in {get_video.__name__} -> {e}")
    else:
        driver.close()
        return video_url
