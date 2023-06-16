from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import datetime
import pytz
import time

class ActivityScraper:

    def __init__(self, driver, strava_athlete_url, delay):
        self.driver = driver
        self.strava_athlete_url = strava_athlete_url
        self.delay = delay

    def timestamp_converter(self, time_text):
        today = datetime.datetime.now(pytz.timezone('US/Pacific'))  # replace with your timezone
        yesterday = today - datetime.timedelta(days=1)
        if 'Today' in time_text:
            time_text = time_text.replace('Today', today.strftime('%b %d, %Y'))
        elif 'Yesterday' in time_text:
            time_text = time_text.replace('Yesterday', yesterday.strftime('%b %d, %Y'))
        dt = datetime.datetime.strptime(time_text, '%B %d, %Y at %I:%M %p')
        epoch = int(dt.timestamp())
        return epoch, dt

    def fetch_activities(self, year, week_number):
        self.driver.get(self.strava_athlete_url)
        id = f"interval-{year}{week_number:02d}"
        #print(id)
        week_button = WebDriverWait(self.driver, self.delay).until(EC.element_to_be_clickable((By.ID, id)))
        week_button.click()
        time.sleep(5)
        parent_div = self.driver.find_element(By.CLASS_NAME, 'feed-ui')
        direct_child_divs = parent_div.find_elements(By.XPATH, './div')
        activity_links = {}   
        for direct_div in direct_child_divs:
            child_divs = direct_div.find_elements(By.XPATH, './div')
            for div in child_divs:
                try:
                    time_element = WebDriverWait(div, self.delay).until(EC.presence_of_element_located((By.XPATH, './/time[@data-testid="date_at_time"]')))
                    time_text = time_element.text
                    epoch_dt, dt = self.timestamp_converter(time_text)
                    link_element = WebDriverWait(div, self.delay).until(EC.presence_of_element_located((By.XPATH, './/a[@data-testid="activity_name"]')))
                    link = link_element.get_attribute("href")
                    activity_links[dt] = link
                except Exception as e:
                    #print(str(e))
                    #print("Time element not found in this div.")
                    continue

        return activity_links
