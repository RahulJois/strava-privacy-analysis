import gpxpy
import pandas as pd
import os
from datetime import datetime
import pytz
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import numpy as np
import folium
import geopy.distance
from scipy.spatial.distance import cdist
from collections import Counter
import calendar

class GPXClusterAnalysis:
    def __init__(self, gpx_directory, local_tz='America/Los_Angeles'):
        self.gpx_directory = gpx_directory
        self.local_tz = pytz.timezone(local_tz)

    def parse_gpx_files(self):
        data = []
        for filename in os.listdir(self.gpx_directory):
            if filename.endswith('.gpx'):
                print(f"Parsing file....{filename}")
                FileID = filename
                gpx_file = open(os.path.join(self.gpx_directory, filename), 'r')
                gpx = gpxpy.parse(gpx_file)
                
                try:
                    for track in gpx.tracks:
                        for segment in track.segments:
                            # Only take the first and last point of each segment
                            start_point = segment.points[0]
                            end_point = segment.points[-1]
                            
                            for point_type, point in zip(['Start', 'End'], [start_point, end_point]):
                                local_time = point.time
                                day_of_week = local_time.isoweekday()
                                hour_of_day = local_time.hour
                                data.append([point.latitude, point.longitude, hour_of_day, day_of_week, point_type, FileID])
                except Exception as e:
                    print(f"Unable to parse {filename}")

        df = pd.DataFrame(data, columns=['Latitude', 'Longitude', 'HourOfDay','DayOfWeek', 'PointType','FileID'])
        df['PointFeature'] = df['PointType'].apply(lambda x: -1 if x == 'Start' else 1)

        self.df = df

    def DBSCAN_clustering(self, eps_radius = 0.1, min_samples = 5):
        coords = self.df[['Latitude', 'Longitude']].values
        coords_rad = np.radians(coords)

        kms_per_radian = 6371.0088
        epsilon = eps_radius / kms_per_radian

        db = DBSCAN(eps=epsilon, min_samples= min_samples, algorithm='ball_tree', metric='haversine').fit(coords_rad)
        self.df['SpatialCluster'] = db.labels_
        print(f"Found {len(self.df['SpatialCluster'].unique()) - 1} unique clusters")

    def hour_scale_and_transform(self, eps = 0.4, min_samples = 5):
        scaler = StandardScaler()
        self.df['HourOfDay_scaled'] = scaler.fit_transform(self.df[['HourOfDay']])

        self.df['Cluster'] = '-1'

        for point_type in ['Start', 'End']:
            subset_df = self.df[self.df['PointType'] == point_type]
            
            for spatial_cluster in subset_df['SpatialCluster'].unique():
                if spatial_cluster == -1:
                    continue
                
                subset = subset_df[subset_df['SpatialCluster'] == spatial_cluster]
                if len(subset) >= min_samples:
                    features = subset[['HourOfDay_scaled', 'PointFeature']].values
                    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
                    clusters = dbscan.fit_predict(features)
                    
                    self.df.loc[(self.df['PointType'] == point_type) & (self.df['SpatialCluster'] == spatial_cluster), 'Cluster'] = [f'{spatial_cluster}_{c}_{point_type}' if c != -1 else "-1" for c in clusters]
        return self.df

    def plot_cluster_map(self, clustering_type='spatial'):
        assert clustering_type in ['spatial', 'both'], \
            "Invalid clustering_type! It should be either 'spatial' or 'both'."


        day_dict = {i: calendar.day_name[i-1] for i in range(1,8)}
        
        # Create map centered on mean coordinates
        non_noise_df = self.df[self.df['Cluster'] != '-1' if clustering_type == 'both' else self.df['SpatialCluster'] != -1]
        map_center = [non_noise_df['Latitude'].mean(), non_noise_df['Longitude'].mean()]
        m = folium.Map(location=map_center, zoom_start=13)

        # Use color palette to distinguish different clusters
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
                'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
                'gray', 'black', 'lightgray']

        # For each cluster, add a feature group to the map, add a circle for each point
        for cluster_id in self.df['Cluster'].unique() if clustering_type == 'both' else self.df['SpatialCluster'].unique():
            if cluster_id == '-1' or cluster_id == -1:
                continue
            fg = folium.FeatureGroup(name=f'Cluster {cluster_id}' if clustering_type == 'both' else f'Spatial Cluster {cluster_id}')
            cluster_data = self.df[self.df['Cluster'] == cluster_id] if clustering_type == 'both' else self.df[self.df['SpatialCluster'] == cluster_id]

            # If both spatial and temporal clustering, calculate 'center of mass' for this cluster
            if clustering_type == 'both':
                cluster_points = cluster_data[['Latitude', 'Longitude']].values
                avg_dists = cdist(cluster_points, cluster_points).mean(axis=1)
                center_of_mass = cluster_points[avg_dists.argmin()]

                # Calculate median 'HourOfDay' for this cluster
                median_hour = cluster_data['HourOfDay'].median()

                # Define cluster color based on first part of cluster ID (splitting by underscore)
                cluster_color_id = int(cluster_id.split('_')[0]) if isinstance(cluster_id, str) else cluster_id
                cluster_color = colors[cluster_color_id % len(colors)]

                for idx, row in cluster_data.iterrows():
                    folium.CircleMarker(location=[row['Latitude'], row['Longitude']],
                                    radius=5,
                                    fill=True,
                                    color=cluster_color,
                                    fill_opacity=0.7).add_to(fg)

                mean_location = [cluster_data['Latitude'].mean(), cluster_data['Longitude'].mean()]
                distances = cluster_data.apply(lambda row: geopy.distance.distance(mean_location, [row['Latitude'], row['Longitude']]).m, axis=1)
                percentile_distance = distances.quantile(0.7)
                
                #common_days = Counter(cluster_data['DayOfWeek']).most_common(2)
                #print(common_days)
                #common_days_str = '<br>'.join(f'{day_dict[day]}: {count}' for day, count in common_days)

                # Get count of activities per day, get the 3 most common days
                activities_per_day = Counter(cluster_data['DayOfWeek'])
                common_days = activities_per_day.most_common(3)
                common_days_str = '<br>'.join(f'{day_dict[day]}: {count}' for day, count in common_days)

                # Draw a circle around the cluster
                folium.Circle(
                    location=center_of_mass,
                    radius=percentile_distance,
                    color=cluster_color,
                    fill=True,
                    fill_opacity=0.2,
                ).add_to(fg)

                folium.Marker(
                    location=center_of_mass,
                    popup=folium.Popup((f'<div style="width:250px">'
                                        f'Cluster ID: {cluster_id}<br>'
                                        f'Lat: {mean_location[0]:.4f}<br>'
                                        f'Lon: {mean_location[1]:.4f}<br>'
                                        f'Hour of Day: {median_hour:.2f}<br>'
                                        f'Most Common Days:<br> {common_days_str}</div>'), max_width=250),
                    icon=folium.Icon(icon="map-marker", prefix='fa')  # Use a marker icon
                ).add_to(fg)


                
            # If only spatial clustering
            else:
                for idx, row in cluster_data.iterrows():
                    folium.CircleMarker(location=[row['Latitude'], row['Longitude']],
                                        radius=5,
                                        fill=True,
                                        color=colors[cluster_id % len(colors)],
                                        fill_opacity=0.7).add_to(fg)

            fg.add_to(m)

        folium.LayerControl().add_to(m)
        return m


# Usage: 
# To plot spatial clusters only: plot_cluster_map(df, 'spatial')
# To plot both spatial and temporal clusters: plot_cluster_map(df, 'both')

