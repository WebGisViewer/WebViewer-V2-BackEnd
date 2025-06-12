import os
import json
import requests
from bs4 import BeautifulSoup
import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping
import random

"""

dynamically get's the centroids, (picks random layers gets the centroids)

dynamically adds the popup template, styling

dynamically detects layer crs (102008, 4326), and layer type 


"""


class WebGISUploader:
    def __init__(self, base_url, username, password, folder_path, config_file, project_name):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.folder_path = folder_path
        self.config_file = config_file
        self.project_name = project_name
        self.session = requests.Session()
        self.csrf_token = None
        self.project_id = None
        self.group_cache = {}

    def authenticate(self):
        login_url = f"{self.base_url}/admin/login/"
        login_page = self.session.get(login_url)
        self.csrf_token = BeautifulSoup(
            login_page.text, "html.parser"
        ).find("input", attrs={"name": "csrfmiddlewaretoken"}).get("value")

        login_data = {
            "username": self.username,
            "password": self.password,
            "csrfmiddlewaretoken": self.csrf_token
        }

        self.session.post(login_url, data=login_data, headers={"Referer": login_url})
        self.csrf_token = self.session.cookies.get("csrftoken")

    def create_project(self):
        payload = {
            "name": self.project_name,
            "description": "Created from folder and config",
            "is_public": True,
            "is_active": True,
            "default_center_lat": self.default_center[0],
            "default_center_lng": self.default_center[1],
            "default_zoom_level": 10,
            "max_zoom": 18,
            "min_zoom": 3,
            "map_controls": {
                "zoomControl": True,
                "scaleControl": False,
                "fullScreenControl": True
            },
            "map_options": {
                "dragging": True,
                "scrollWheelZoom": False,
                "doubleClickZoom": True,
                "keyboard": True
            }
        }
        headers = {"X-CSRFToken": self.csrf_token}
        response = self.session.post(f"{self.base_url}/api/v1/projects/", json=payload, headers=headers)
        self.project_id = response.json()["id"]
        print(f"✅ Project created: {self.project_id}")
        self.add_base_maps()

    def add_base_maps(self):
        basemaps = [
            {"name": "White Background", "provider": "blank", "url_template": "", "attribution": "White Background"},
            {"name": "Google Maps", "provider": "custom", "url_template": "http://www.google.cn/maps/vt?lyrs=m&x={x}&y={y}&z={z}", "attribution": "Google Maps"},
            {"name": "Google Satellite", "provider": "custom", "url_template": "http://www.google.cn/maps/vt?lyrs=s&x={x}&y={y}&z={z}", "attribution": "Google Satellite"}
        ]
        for idx, basemap in enumerate(basemaps, start=1):
            payload = {
                "project": self.project_id,
                "basemap": idx,
                "is_default": idx == 2,
                "display_order": idx,
                "custom_options": {}
            }
            self.session.post(
                f"{self.base_url}/api/v1/project-basemaps/",
                json=payload,
                headers={"X-CSRFToken": self.csrf_token}
            )
            print(f"🗺️ Added basemap: {basemap['name']}")

    def get_or_create_group(self, name, order):
        if name in self.group_cache:
            return self.group_cache[name]

        payload = {
            "name": name,
            "project": self.project_id,
            "display_order": order,
            "is_visible_by_default": True,
            "is_expanded_by_default": False
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/layer-groups/",
            json=payload,
            headers={"X-CSRFToken": self.csrf_token}
        )
        group_id = response.json()["id"]
        self.group_cache[name] = group_id
        print(f"📁 Group '{name}' created (ID: {group_id})")
        return group_id

    def detect_crs_by_bounds(self, gdf):
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        if abs(bounds[0]) > 180 or abs(bounds[2]) > 180:
            gdf = gdf.set_crs("ESRI:102008", allow_override=True).to_crs("EPSG:4326")
        else:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        return gdf

    def get_centroid_coordinates(self, gdf):
        centroid = gdf.geometry.centroid.unary_union.centroid
        return centroid.y, centroid.x  # latitude, longitude

    def detect_geometry_type(self, gdf):

        return gdf.geometry.geom_type.mode()[0]  # most common geometry type

    def create_style(self, style_def, layer_id):
        payload = {
            "name": f"Style for layer {layer_id}",
            "description": f"Auto-generated style for layer {layer_id}",
            "style_type": "point",
            "style_definition": style_def,
            "is_system": False
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/styles/",
            json=payload,
            headers={"X-CSRFToken": self.csrf_token}
        )
        return response.json().get("id") if response.status_code == 201 else None

    def apply_style(self, style_id, layer_id):
        payload = {"layer_id": layer_id}
        response = self.session.post(
            f"{self.base_url}/api/v1/styles/{style_id}/apply_to_layer/",
            json=payload,
            headers={"X-CSRFToken": self.csrf_token}
        )
        return response.status_code == 200

    def upload_layer_data(self, layer_id, file_path, crs, column_names, chunk_size=500):


        gdf = gpd.read_file(file_path)
        gdf = self.detect_crs_by_bounds(gdf)

        features = [
            {"type": "Feature", "geometry": mapping(row.geometry), "properties": {
                col: None if pd.isna(row.get(col)) else row.get(col) for col in column_names
            }} for _, row in gdf.iterrows()
        ]

        total_uploaded = 0
        for i in range(0, len(features), chunk_size):
            chunk = features[i:i + chunk_size]
            geojson_data = {"type": "FeatureCollection", "features": chunk}
            response = self.session.post(
                f"{self.base_url}/api/v1/layers/{layer_id}/import_geojson/",
                json=geojson_data,
                headers={"X-CSRFToken": self.csrf_token}
            )
            if not response.ok:
                print(f"❌ Error uploading batch {i // chunk_size + 1}: {response.text}")
                return
            total_uploaded += len(chunk)
            print(f"✅ Uploaded batch {i // chunk_size + 1}: {len(chunk)} features")
        print(f"🎉 Done! Uploaded {total_uploaded} features to layer {layer_id}")

    def create_popup_templates(self, layers):
        print("✨ Creating popup templates...")
        templates = {}
        for layer in layers:
            if not layer.get("columns_for_popup"):
                continue

            key = layer["layer_name"]
            columns = layer["columns_for_popup"]
            title = layer.get("title", key)
            table_class = "popup-table"

            rows_html = "\n".join([
                f"<tr><td><b>{col}</b></td><td>{{{{{col}}}}}</td></tr>" for col in columns
            ])

            html_template = f"""<style>
            .{table_class} {{
                width: 100%;
                border-collapse: collapse;
                font-family: Arial, sans-serif;
            }}
            .{table_class} td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            .{table_class} tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .{table_class} tr:hover {{ background-color: #ddd; }}
            </style>
            <b>{title}</b>
            <table class='{table_class}'>{rows_html}</table>"""

            payload = {
                "name": key,
                "description": f"Popup for {key}",
                "html_template": html_template,
                "field_mappings": {col: col for col in columns},
                "css_styles": "",
                "max_width": 400,
                "max_height": 400,
                "include_zoom_to_feature": True
            }

            response = self.session.post(
                f"{self.base_url}/api/v1/popup-templates/",
                json=payload,
                headers={"X-CSRFToken": self.csrf_token}
            )
            if response.status_code == 201:
                templates[key] = response.json()["id"]
                print(f"✅ Created popup template: {key}")
            else:
                print(f"❌ Failed to create popup template: {key}")
        return templates
    
    # def extract_random_layer_centroid(self, config):
    #     layers_with_files = [layer for layer in config if os.path.exists(os.path.join(self.folder_path, layer['group'], layer['filename']))]
    #     if not layers_with_files:
    #         print("❌ No valid layers with existing files found.")
    #         return
    #     sample_layer = random.choice(layers_with_files)
    #     gdf = gpd.read_file(os.path.join(self.folder_path, sample_layer['group'], sample_layer['filename']))
    #     gdf = self.detect_crs_by_bounds(gdf)
    #     lat, lng = self.get_centroid_coordinates(gdf)
    #     self.default_center = [lat, lng]
    #     print(f"📍 Default center extracted from layer '{sample_layer['layer_name']}': {self.default_center}")


    def extract_random_layer_centroid(self, config):
        layers_with_files = [layer for layer in config if os.path.exists(os.path.join(self.folder_path, layer['group'], layer['filename']))]
        if not layers_with_files:
            print("❌ No valid layers with existing files found.")
            return

        selected_layers = random.sample(layers_with_files, min(3, len(layers_with_files)))
        centroids = []

        for layer in selected_layers:
            try:
                gdf = gpd.read_file(os.path.join(self.folder_path, layer['group'], layer['filename']))
                gdf = self.detect_crs_by_bounds(gdf)
                lat, lng = self.get_centroid_coordinates(gdf)
                centroids.append((lat, lng))
                print(centroids)
            except Exception as e:
                print(f"⚠️ Skipping layer '{layer['layer_name']}' due to error: {e}")

        if centroids:
            avg_lat = sum(c[0] for c in centroids) / len(centroids)
            avg_lng = sum(c[1] for c in centroids) / len(centroids)
            self.default_center = [avg_lat, avg_lng]
            print(f"📍 Average center from {len(centroids)} layers: {self.default_center}")
        else:
            print("❌ Failed to compute centroid from selected layers.")

    def process_layer(self, layer, popup_templates):
        file_path = os.path.join(self.folder_path, layer['group'], layer["filename"])
        group_id = self.get_or_create_group(layer["group"], layer['display_order'])
        popup_template_id = popup_templates.get(layer["layer_name"])

        payload = {
            "project_layer_group": group_id,
            "layer_type": layer["layer_type_id"],
            "name": layer["layer_name"],
            "description": "Auto-created layer",
            "style_id": layer.get("style", {}),
            "z_index": 2,
            "is_visible_by_default": True,
            "popup_template": popup_template_id,
            "display_order": layer['display_order']
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/layers/",
            json=payload,
            headers={"X-CSRFToken": self.csrf_token}
        )
        if response.status_code != 201:
            print(f"❌ Failed to create layer {layer['layer_name']}")
            return

        layer_id = response.json()["id"]
        print(f"✅ Layer created: {layer['layer_name']} (ID: {layer_id})")

        self.upload_layer_data(layer_id, file_path, layer["source_crs"], layer.get("columns_for_popup", []))

        if "style" in layer:
            style_id = self.create_style(layer["style"], layer_id)
            if style_id and self.apply_style(style_id, layer_id):
                print(f"🎨 Style applied to layer {layer_id}")

    def run(self):

        with open(self.config_file, "r") as f:
            config = json.load(f)

        self.authenticate()

        self.extract_random_layer_centroid(config)

        self.create_project()

        popup_templates = self.create_popup_templates(config)

        for layer in config:
            self.process_layer(layer, popup_templates)

        print("✅ All layers processed.")


if __name__ == "__main__":

    uploader = WebGISUploader(
        base_url="http://127.0.0.1:8000",
        username="adminuser",
        password="levon",
        folder_path="/Users/levon/Desktop/WebGIS/WebViewer-V2-BackEnd/new_Test_Project sample",  # change this
        config_file="/Users/levon/Desktop/WebGIS/WebViewer-V2-BackEnd/new_Test_Project sample/polygon_layers_config.json",  # change this
        project_name="Maricopa Project -2"
    )

    uploader.run()