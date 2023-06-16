from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from typing import Tuple
from gpx_downloader import GPXDownloader
from gpx_processor import GPXProcessor
import constants

class ActivityProcessor:

    def __init__(self, driver, total_activities, acitivity_links,activity_data) -> None:
        self.acitivity_links = acitivity_links
        self.driver = driver
        self.activity_count = total_activities
        self.activity_data = activity_data

    def actitivity_processor(self,cookie_file) -> Tuple[list,int]:
        for start_time,activity in self.acitivity_links.items():
            self.activity_dict = {}
            self.driver.get(f"{activity}/overview")
            #print(f"Activitiy Count: {self.activity_count}")
            try:
                title_element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, './/h2[@class="text-title3 text-book marginless"]/span[@class="title"]')))
                title_text = title_element.text
                
                # Split the title text by newline and get the activity, which seems to be on the second line
                activity_title = title_text.split("\n")[-1].strip()
                #print("Activity:", activity_title)
                #print(f"Date: {start_time.day}th {start_time.strftime('%B')}, {start_time.year}")

                #Distance Element
                distance_li = self.driver.find_element(By.XPATH, '//ul[@class="inline-stats section"]/li[div[text()="Distance"]]')
                distance = distance_li.find_element(By.TAG_NAME, 'strong').text
                self.activity_dict['distance'] = distance.split('km')[0].rstrip()
                self.activity_dict['activity_id'] = activity.split('/')[-1]

                if 'run' in title_text.lower():
                    self.activity_dict['activity_type'] = "run"
                    mile_splits_div = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'mile-splits')))
                    table_body = WebDriverWait(mile_splits_div, 10).until(EC.presence_of_element_located((By.ID, 'contents')))
                    mile_split_dict = {}
                    rows = table_body.find_elements(By.TAG_NAME, 'tr')
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        mile_split_dict[float(cells[0].text)] = cells[1].text.split('/km')[0].rstrip()
                    self.activity_dict['mile_splits'] = mile_split_dict

                elif 'ride' in title_text.lower():
                    self.activity_dict['activity_type'] = "ride"
                    self.activity_dict['mile_splits'] = {}
                    # Average Speed Element
                    speed_row = self.driver.find_element(By.XPATH, '//th[text()="Speed"]/ancestor::tr')
                    avg_speed_cell = speed_row.find_element(By.XPATH, './td[1]')
                    avg_speed = avg_speed_cell.text.split(' ')[0]
                    self.activity_dict['average_speed'] = avg_speed

                if self.activity_dict['activity_type'] in ['ride','run']:
                    self.gpx_download(self.activity_dict['activity_id'],self.activity_dict['activity_type'],cookie_file)
                    #print(f"{constants.OUTPUT_PATH}{self.activity_dict['activity_type']}/{self.activity_dict['activity_id']}.gpx")
                    gpx_processor = GPXProcessor(f"{constants.OUTPUT_PATH}/{self.activity_dict['activity_type']}/{self.activity_dict['activity_id']}.gpx", start_time.isoformat() + 'Z', self.activity_dict['mile_splits'])
                    #print(self.activity_dict)
                    if self.activity_dict['activity_type'] == 'run':
                        gpx_processor.add_time_data_to_gpx_for_run()
                    elif self.activity_dict['activity_type'] == 'ride':
                        gpx_processor.add_time_data_to_gpx_for_ride(self.activity_dict['average_speed'])
                    #print(f"{constants.OUTPUT_PATH}timestamp/{self.activity_dict['activity_type']}/{self.activity_dict['activity_id']}.gpx")
                    gpx_processor.write_gpx_file(f"{constants.OUTPUT_PATH}timestamp/{self.activity_dict['activity_type']}/{self.activity_dict['activity_id']}.gpx")

            except Exception as e:
                #print(str(e))
                #print("Title element not found in this div.")
                continue
            self.activity_data.append(self.activity_dict)
            self.activity_count += 1

        return self.activity_data,self.activity_count    
    
    def gpx_download(self,activity_id,activitiy_type,cookie_file) -> None:
        downloader = GPXDownloader(activity_id, activitiy_type, cookie_file)
        downloader.run()

'''
start_time = "2023-05-07T08:16:00Z"
km_splits = {
    1: "05:37",
    2: "04:45",
    3: "05:22",
    4: "05:19",
    5: "04:45",
    6: "04:43",
    7: "04:45",
    8: "04:49",
    9: "04:24",
    10: "04:34",
    0.25: "7.22"
}

gpx_processor = GPXProcessor("gpx_without_timestamp_2.gpx", start_time, km_splits)
gpx_processor.add_time_data_to_gpx()
gpx_processor.write_gpx_file("gpx_with_timestamps_2.gpx")
'''