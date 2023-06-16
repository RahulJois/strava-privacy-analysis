import json
import requests
import constants
import os

class GPXDownloader:
    def __init__(self, activity_id, activity_type, cookie_file):
        self.activity_id = activity_id
        self.cookie_file = cookie_file
        self.output_path = f"{constants.OUTPUT_PATH}{activity_type}/{self.activity_id}.gpx"
        self.headers = self.get_cookie_headers()
        self.url = constants.GPX_DOWNLOAD_URL.replace("{activity_id}",self.activity_id)

    def get_cookie_headers(self):
        with open(self.cookie_file, 'r') as f:
            cookies = json.load(f)

        cookie_str = ""
        for cookie in cookies:
            cookie_str += cookie['name'] + "=" + cookie['value'] + "; "

        return {
            'Cookie': cookie_str.rstrip('; ')
        }

    def download_gpx(self):
        response = requests.get(self.url, headers=self.headers)
        return response.text

    def save_gpx(self, gpx_data):
        dir_name = os.path.dirname(self.output_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        with open(self.output_path, 'w') as f:
            f.write(gpx_data)

    def run(self):
        gpx_data = self.download_gpx()
        self.save_gpx(gpx_data)


