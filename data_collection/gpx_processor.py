from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from math import radians, cos, sin, asin, sqrt
import os

class GPXProcessor:
    ET.register_namespace("", "http://www.topografix.com/GPX/1/1")
    
    def __init__(self, file_path, start_time, km_splits):
        self.file_path = file_path
        self.start_time = start_time
        self.km_splits = km_splits
        self.tree, self.trkpts = self.read_gpx_file(self.file_path)
    
    @staticmethod
    def read_gpx_file(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        trkpts = root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")
        return tree, trkpts

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 
        return c * r * 1000

    @staticmethod
    def add_seconds_to_time(iso_time, seconds):
        time_obj = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        new_time_obj = time_obj + timedelta(seconds=seconds)
        return new_time_obj.isoformat().replace("+00:00", "Z")

    def add_time_data_to_gpx_for_ride(self, avg_speed_kmh):
        # Convert average speed from km/h to m/s
        avg_speed_ms = float(avg_speed_kmh) * 1000 / 3600

        current_time = self.start_time
        total_distance = 0

        for i in range(len(self.trkpts)):
            if i == 0:
                time_elem = ET.Element("time")
                time_elem.text = current_time
                self.trkpts[i].append(time_elem)
            else:
                lat1, lon1 = map(float, (self.trkpts[i-1].attrib["lat"], self.trkpts[i-1].attrib["lon"]))
                lat2, lon2 = map(float, (self.trkpts[i].attrib["lat"], self.trkpts[i].attrib["lon"]))
                distance = self.haversine(lon1, lat1, lon2, lat2)
                total_distance += distance

                time_to_add = distance / avg_speed_ms

                current_time = self.add_seconds_to_time(current_time, time_to_add)
                time_elem = ET.Element("time")
                time_elem.text = current_time
                self.trkpts[i].append(time_elem)




    def add_time_data_to_gpx_for_run(self):
        current_time = self.start_time
        total_distance = 0
        km_distance = 0
        points_in_current_km = []
        gpx_points_per_km = {}
        
        for i in range(len(self.trkpts)):
            if i != 0:
                lat1, lon1 = map(float, (self.trkpts[i-1].attrib["lat"], self.trkpts[i-1].attrib["lon"]))
                lat2, lon2 = map(float, (self.trkpts[i].attrib["lat"], self.trkpts[i].attrib["lon"]))
                distance = self.haversine(lon1, lat1, lon2, lat2)
                total_distance += distance
                km_distance += distance

            points_in_current_km.append(self.trkpts[i])

            if km_distance >= 1000 or i == len(self.trkpts) - 1:
                km_number = int(total_distance // 1000)
                gpx_points_per_km[km_number] = points_in_current_km
                points_in_current_km = []
                km_distance %= 1000

        for km_number, points_in_current_km in gpx_points_per_km.items():
            split_time = self.km_splits.get(km_number)
            if split_time is not None:
                minutes, seconds = map(int, split_time.split(":"))
                time_to_add = minutes * 60 + seconds
                time_increment = time_to_add / len(points_in_current_km)
                for _, point in enumerate(points_in_current_km):
                    current_time = self.add_seconds_to_time(current_time, time_increment)
                    time_elem = ET.Element("{http://www.topografix.com/GPX/1/1}time")
                    time_elem.text = current_time
                    point.append(time_elem)

    def write_gpx_file(self, output_file_path):
        dir_name = os.path.dirname(output_file_path)
        #print(f"Dir Name:{dir_name}")
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        #print("Writing...")
        self.tree.write(output_file_path, default_namespace='')



