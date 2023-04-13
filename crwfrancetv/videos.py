from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException
import time


def get_video(url):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)


    # disagree_button = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH,
    #                                 '//button[@class="didomi-components-button didomi-button didomi-\
    #                                     disagree-button didomi-button-standard standard-button"]'))
    # )
    time.sleep(10)
    disagree_button = driver.find_element(By.XPATH, '//button[@class="didomi-components-button didomi-button didomi-disagree-button didomi-button-standard standard-button"]')
    disagree_button.click()
    time.sleep(5)
    play_button = driver.find_element(By.XPATH, '//div[@role="presentation"]')
    time.sleep(5)
    # breakpoint()
    play_button.click()

    # try:
    play_button = driver.find_element(By.XPATH, '//div[@class="ftv-magneto--btn ftv-magneto--focusable-item"]')
    play_button.click()
    # except ElementClickInterceptedException:
    #     WebDriverWait(driver, 10).until_not(EC.presence_of_element_located((By.XPATH,
    #                                                                         '//div[@class="ftv-magneto--btn \
    #                                                                             ftv-magneto--focusable-item"]')))

    time.sleep(10)
    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.XPATH, '//div[@role="dialog"]//div[@role="presentation"]/span')))
    iframe_text = driver.find_element(By.XPATH, '//div[@role="dialog"]//div[@role="presentation"]/span')
    text = iframe_text.text
    breakpoint()
    text = text.split('//')
    text = text[1].split('"')[0]
    driver.close()
    return f"https://{text}"

print(get_video('https://www.francetvinfo.fr/faits-divers/xavier-dupont-de-ligonnes/video-affaire-dupont-de-ligonnes-pas-une-seule-trace-de-sang-dans-la-maison-c-est-unique-je-crois-ne-l-avoir-jamais-vu_5755739.html'))
