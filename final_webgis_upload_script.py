
import os
import json
import requests
from bs4 import BeautifulSoup
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import mapping

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "adminuser"
PASSWORD = "levon"
FOLDER_PATH = "/Users/levon/Desktop/WebGIS/WebViewer-V2-BackEnd/Test_Project"
CONFIG_FILE = os.path.join(FOLDER_PATH, "new_json.json")
PROJECT_NAME = "Callam PRJ with Custom Styles Uploaded with cleaned script 2"

session = requests.Session()
csrf_token = None
PROJECT_ID = None
group_cache = {}

def authenticate():
    global csrf_token
    login_url = f"{BASE_URL}/admin/login/"
    login_page = session.get(login_url)
    csrf_token = BeautifulSoup(login_page.text, "html.parser").find("input", attrs={"name": "csrfmiddlewaretoken"}).get("value")
    login_data = {"username": USERNAME, "password": PASSWORD, "csrfmiddlewaretoken": csrf_token}
    session.post(login_url, data=login_data, headers={"Referer": login_url})
    csrf_token = session.cookies.get("csrftoken")

def create_project():
    global PROJECT_ID
    payload = {
        "name": PROJECT_NAME,
        "description": "Created from folder and config",
        "is_public": True,
        "is_active": True,
        "default_center_lat": 0.0,
        "default_center_lng": 0.0,
        "default_zoom_level": 4,
        "max_zoom": 18,
        "min_zoom": 3,
        "map_controls": {"zoomControl": True, "scaleControl": False, "fullScreenControl": True},
        "map_options": {"dragging": True, "scrollWheelZoom": False, "doubleClickZoom": True, "keyboard": True}
    }
    headers = {"X-CSRFToken": csrf_token}
    resp = session.post(f"{BASE_URL}/api/v1/projects/", json=payload, headers=headers)
    PROJECT_ID = resp.json()["id"]
    print("✅ Project created:", PROJECT_ID)
    add_base_maps(PROJECT_ID)

def get_or_create_group(name):
    if name in group_cache:
        return group_cache[name]
    payload = {
        "name": name,
        "project": PROJECT_ID,
        "display_order": 1,
        "is_visible_by_default": True,
        "is_expanded_by_default": False
    }
    resp = session.post(f"{BASE_URL}/api/v1/layer-groups/", json=payload, headers={"X-CSRFToken": csrf_token})
    group_id = resp.json()["id"]
    group_cache[name] = group_id
    print(f"📁 Group '{name}' created (ID: {group_id})")
    return group_id

def create_style(style_def, layer_id):
    payload = {
        "name": f"Style for layer {layer_id}",
        "description": f"Auto-generated style for layer {layer_id}",
        "style_type": "point",
        "style_definition": style_def,
        "is_system": False
    }
    resp = session.post(f"{BASE_URL}/api/v1/styles/", json=payload, headers={"X-CSRFToken": csrf_token})
    return resp.json().get("id") if resp.status_code == 201 else None

def apply_style(style_id, layer_id):
    payload = {"layer_id": layer_id}
    resp = session.post(f"{BASE_URL}/api/v1/styles/{style_id}/apply_to_layer/", json=payload, headers={"X-CSRFToken": csrf_token})
    return resp.status_code == 200

def upload_layer_data(layer_id, file_path, column_names, chunk_size=500):
    gdf = gpd.read_file(file_path).set_crs("EPSG:4326", allow_override=True)
    features = []
    for _, row in gdf.iterrows():
        properties = {col: None if pd.isna(row.get(col)) else row.get(col) for col in column_names}
        features.append({"type": "Feature", "geometry": mapping(row.geometry), "properties": properties})
    total_uploaded = 0
    for i in range(0, len(features), chunk_size):
        chunk = features[i:i + chunk_size]
        geojson_data = {"type": "FeatureCollection", "features": chunk}
        response = session.post(f"{BASE_URL}/api/v1/layers/{layer_id}/import_geojson/", json=geojson_data, headers={"X-CSRFToken": csrf_token})
        if not response.ok:
            print(f"❌ Error uploading batch {i // chunk_size + 1}: {response.text}")
            return
        total_uploaded += len(chunk)
        print(f"✅ Uploaded batch {i // chunk_size + 1}: {len(chunk)} features")
    print(f"🎉 Done! Uploaded {total_uploaded} features to layer {layer_id}")

def create_popup_templates(templates_config):
    print("✨ Creating popup templates...")
    templates = {}
    for config in templates_config:
        key = config['key']
        name = config['name']
        columns = config['columns']
        title = config.get("title", name)
        table_class = config.get("table_class", "popup-table")
        color_theme = config.get("color_theme", "#2196F3")
        rows_html = "\n".join([f"<tr><td><b>{col}</b></td><td>{{{{{col}}}}}</td></tr>" for col in columns])
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
            "name": name,
            "description": config["description"],
            "html_template": html_template,
            "field_mappings": {col: col for col in columns},
            "css_styles": "",
            "max_width": 400,
            "max_height": 400,
            "include_zoom_to_feature": True
        }
        resp = session.post(f"{BASE_URL}/api/v1/popup-templates/", json=payload, headers={"X-CSRFToken": csrf_token})
        if resp.status_code == 201:
            templates[key] = resp.json()["id"]
            print(f"✅ Created popup template: {name}")
    return templates

def add_base_maps(project_id):
    basemaps = [
        {"name": "White Background", "provider": "blank", "url_template": "", "attribution": "White Background"},
        {"name": "Google Maps", "provider": "custom", "url_template": "http://www.google.cn/maps/vt?lyrs=m&x={x}&y={y}&z={z}", "attribution": "Google Maps"},
        {"name": "Google Satellite", "provider": "custom", "url_template": "http://www.google.cn/maps/vt?lyrs=s&x={x}&y={y}&z={z}", "attribution": "Google Satellite"}
    ]
    for idx, basemap in enumerate(basemaps, start=1):
        payload = {
            "project": project_id,
            "basemap": idx,
            "is_default": idx == 2,
            "display_order": idx,
            "custom_options": {}
        }
        session.post(f"{BASE_URL}/api/v1/project-basemaps/", json=payload, headers={"X-CSRFToken": csrf_token})
        print(f"🗺️ Added basemap: {basemap['name']}")

def process_layer(layer, popup_templates):
    file_path = os.path.join(FOLDER_PATH, layer["filename"])
    group_id = get_or_create_group(layer["group"])
    popup_template_id = None
    if layer.get("columns_for_popup"):
        popup_template_id = popup_templates.get(layer["layer_name"])
    layer_payload = {
        "project_layer_group": group_id,
        "layer_type": layer["layer_type_id"],
        "name": layer["layer_name"],
        "description": "Auto-created layer",
        "style": layer.get("style", {}),
        "z_index": 2,
        "is_visible_by_default": True,
        "popup_template": popup_template_id
    }
    resp = session.post(f"{BASE_URL}/api/v1/layers/", json=layer_payload, headers={"X-CSRFToken": csrf_token})
    if resp.status_code != 201:
        print(f"❌ Failed to create layer {layer['layer_name']}")
        return
    layer_id = resp.json()["id"]
    print(f"✅ Layer created: {layer['layer_name']} (ID: {layer_id})")
    upload_layer_data(layer_id, file_path, layer.get("columns_for_popup", []))
    if "style" in layer:
        style_id = create_style(layer["style"], layer_id)
        if style_id and apply_style(style_id, layer_id):
            print(f"🎨 Style applied to layer {layer_id}")

def main():
    authenticate()
    create_project()
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    templates_config = [
        {
            "key": layer["layer_name"],
            "name": layer["layer_name"],
            "description": "Popup for " + layer["layer_name"],
            "columns": layer["columns_for_popup"],
            "title": layer["layer_name"],
            "color_theme": "#01fbff",
            "table_class": "popup-table"
        } for layer in config if layer.get("columns_for_popup")
    ]
    popup_templates = create_popup_templates(templates_config)
    for layer in config:
        process_layer(layer, popup_templates)
    print("✅ All layers processed.")

if __name__ == "__main__":
    main()
