from login_module import StravaLogin
from fetch_activities import ActivityScraper
from activity_processor import ActivityProcessor
from gpx_downloader import GPXDownloader
from gpx_processor import GPXProcessor
from triangulation import GPXClusterAnalysis

import constants
import time
import datetime
from dotenv import dotenv_values
import logging
import shutil
import os
import subprocess


config = dotenv_values(".env")
strava_login = StravaLogin(config['EMAIL_ADDRESS'], config['PASSWORD'])
strava_login.login()
strava_login.store_cookies(f"{constants.COOKIE_FILE_NAME}")
driver = strava_login.get_driver()

now = datetime.datetime.now()
year = now.year
week_number = int(now.strftime("%U"))
num_weeks = 11
strava_athlete_url = f"https://www.strava.com/athletes/{constants.ATHLETE_ID}"
delay = 1
total_activity_count = 0
activity_data = []
#print("Week number:", week_number)
for i in range(week_number,week_number - num_weeks,-1):
    print(f"Processing Week {i}")
    scraper = ActivityScraper(driver, strava_athlete_url, delay)
    activity_links = scraper.fetch_activities(year, i)
    #print(activity_links,len(activity_links))
    processor = ActivityProcessor(driver,total_activity_count, activity_links,activity_data)
    activity_data, total_activity_count = processor.actitivity_processor(constants.COOKIE_FILE_NAME)
    print(f"Total Activities Processed: {total_activity_count}")

driver.quit()

for activity_type in ['ride','run']:
    analysis = GPXClusterAnalysis(gpx_directory=f"{constants.ATHLETE_ID}/timestamp/{activity_type}")
    analysis.parse_gpx_files()
    analysis.DBSCAN_clustering()
    df = analysis.hour_scale_and_transform()
    m = analysis.plot_cluster_map(clustering_type='both')
    m.save(f"map_{activity_type}.html")  # Save map to HTML file


    clusters_list = list(df['Cluster'].unique())
    destination_dir_base = 'heatmap_folder_' + activity_type
    gpx_directory = constants.ATHLETE_ID + '/timestamp/' + activity_type
    heatmap_script_path = './strava_local_heatmap.py'

    for cluster in clusters_list:
        if (cluster != '-1') and ('End' not in cluster):
            files = df[df['Cluster'] == cluster]['FileID'].unique()
            destination_dir = os.path.join(destination_dir_base, str(cluster))
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            for file in files:
                source_file = os.path.join(gpx_directory, file)
                destination_file = os.path.join(destination_dir, file)
                shutil.copy2(source_file, destination_file)  # copies with metadata
            print(f"Copied files for cluster {cluster} to {destination_dir}")
    
            destination_dir = os.path.join(destination_dir_base, str(cluster))
            # Check if the directory exists and it's not empty
            if os.path.exists(destination_dir) and os.listdir(destination_dir):
                print(destination_dir)
                command = f"python3 {heatmap_script_path} --dir {destination_dir} --csv"
                process = subprocess.run(command,shell=True)
                copy_csv_command = f"cp heatmap.csv {destination_dir}"
                process = subprocess.run(copy_csv_command,shell=True)
                copy_png_command = f"cp heatmap.png {destination_dir}"
                process = subprocess.run(copy_png_command,shell=True)    
    

