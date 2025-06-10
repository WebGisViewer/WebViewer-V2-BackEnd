import os
import json
import requests
from bs4 import BeautifulSoup
import geopandas as gpd
import numpy as np
from typing import Dict, List
import json


BASE_URL = "http://127.0.0.1:8000"
USERNAME = "adminuser"
PASSWORD = "levon"

#INPUTS
FOLDER_PATH = "/Users/levon/Desktop/WebGIS/WebViewer-V2-BackEnd/Test_Project"
CONFIG_FILE = os.path.join(FOLDER_PATH, "layer_config.json")
PROJECT_NAME = "Callam PRJ with Custom Styles Uploaded with cleaned script"

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
    print("Project created:", PROJECT_ID)
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
    resp = session.post(f"{BASE_URL}/api/v1/layer-groups/", json=payload, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})
    group_id = resp.json()["id"]
    group_cache[name] = group_id
    print(f"📁 Group '{name}' created (ID: {group_id})")
    return group_id


def upload_layer_file(file_path):
    with open(file_path, "rb") as f:
        resp = session.post(
            f"{BASE_URL}/api/v1/upload/",
            headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL},
            files={"file": f}
        )
    return resp.json() if resp.status_code == 200 else None


import pandas as pd

from shapely.geometry import mapping


def upload_layer_with_selected_columns(session, csrf_token: str, api_base_url: str,
                                       layer_id: int, file_path: str,
                                       column_names, chunk_size = 500):
    """
    Uploads geometry and selected feature attributes to a layer.

    :param session: requests.Session() object with login
    :param csrf_token: string token from Django
    :param api_base_url: your API endpoint base (e.g., http://127.0.0.1:8000/api/v1)
    :param layer_id: target layer ID
    :param file_path: path to .sqlite or .kml file
    :param column_names: list of column names to include in feature properties
    :param chunk_size: upload size per batch
    """
    gdf = gpd.read_file(file_path).set_crs("EPSG:4326", allow_override=True)

    features = []
    for _, row in gdf.iterrows():
        properties = {}
        for col in column_names:
            val = row.get(col)
            if pd.isna(val):
                properties[col] = None
            elif isinstance(val, (float, np.floating)):
                properties[col] = None if np.isnan(val) or np.isinf(val) else float(val)
            elif isinstance(val, (int, np.integer)):
                properties[col] = int(val)
            else:
                properties[col] = str(val) if val is not None else None

        features.append({
            "type": "Feature",
            "geometry": mapping(row.geometry),
            "properties": properties
        })

    total_uploaded = 0
    for i in range(0, len(features), chunk_size):
        chunk = features[i:i + chunk_size]
        geojson_data = {
            "type": "FeatureCollection",
            "features": chunk
        }

        response = session.post(
            f"{api_base_url}/layers/{layer_id}/import_geojson/",
            json=geojson_data,
            headers={
                "X-CSRFToken": csrf_token,
                "Referer": api_base_url
            }
        )
        if not response.ok:
            print(f"❌ Error uploading batch {i // chunk_size + 1}")
            print(response.text)
            return

        total_uploaded += len(chunk)
        print(f"✅ Uploaded batch {i // chunk_size + 1}: {len(chunk)} features")

    print(f"\n🎉 Done! Uploaded {total_uploaded} features to layer {layer_id}")



def complete_layer_upload(layer, upload_data, group_id):

    payload = {
        "file_id": upload_data["file_id"],
        "file_type": upload_data["file_type"],
        "group_id": group_id,
        "layer_name": layer["layer_name"],
        "layer_type_id": layer["layer_type_id"],
        "source_crs": layer["source_crs"],
        "target_crs": layer["target_crs"],
        "description": "Uploaded via script",
        "is_visible": True,
        "is_public": True,
        "file_name": upload_data["file_name"],
        "is_visible_by_defult": True,
        "popup_template": 1  # Can be dynamically inserted here
    }

    resp = session.post(f"{BASE_URL}/api/v1/complete_upload/", json=payload, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})
    return resp.json().get("layer_id") if resp.status_code == 200 else None


def create_style(style_def, layer_id):
    payload = {
        "name": f"Style for layer {layer_id}",
        "description": f"Auto-generated style for layer {layer_id}",
        "style_type": "point",
        "style_definition": style_def,
        "is_system": False
    }
    resp = session.post(f"{BASE_URL}/api/v1/styles/", json=payload, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})
    return resp.json().get("id") if resp.status_code == 201 else None


def apply_style(style_id, layer_id):
    payload = {"layer_id": layer_id}
    resp = session.post(f"{BASE_URL}/api/v1/styles/{style_id}/apply_to_layer/", json=payload, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})
    return resp.status_code == 200


def process_layer(layer):
    
    file_path = os.path.join(FOLDER_PATH, layer["filename"])
    print(f"Processing file: {layer['filename']}")
    upload_data = upload_layer_file(file_path)

    if not upload_data:
        print(f"Upload failed for {layer['filename']}")
        return

    group_id = get_or_create_group(layer["group"])

    layer_id = complete_layer_upload(layer, upload_data, group_id)

    if not layer_id:
        print(f"Failed to complete upload for {layer['filename']}")
        return

    print(f"Layer '{layer['layer_name']}' uploaded (ID: {layer_id})")

    style_id = layer.get("style_id")
    if "style" in layer:
        style_id = create_style(layer["style"], layer_id)

    if style_id and apply_style(style_id, layer_id):
        print(f"Style applied to layer {layer_id}")
    else:
        print(f"Failed to apply style for layer {layer_id}")


def add_base_maps(project_id):


    basemaps_to_add = [
                {
                    "name": "White Background",
                    "provider": "blank",
                    "url_template": "",
                    "attribution": "White Background"
                },
                {
                    "name": "Google Maps",
                    "provider": "custom",
                    "url_template": "http://www.google.cn/maps/vt?lyrs=m&x={x}&y={y}&z={z}",
                    "attribution": "Google Maps"
                },
                {
                    "name": "Google Satellite",
                    "provider": "custom",
                    "url_template": "http://www.google.cn/maps/vt?lyrs=s&x={x}&y={y}&z={z}",
                    "attribution": "Google Satellite"
                }
            ]

    for ind, dict_ in enumerate(basemaps_to_add):
        ind+=1
            
        project_basemap_data = {
                        "project": project_id,  # The POST data uses 'project', not 'project_id'
                        "basemap": ind,
                        "is_default":  ind == 2,  # Make Google Maps default
                        "display_order": 1,
                        "custom_options": {}
                    }


        response = session.post(
                            f"{BASE_URL}/api/v1/project-basemaps/",
                            json=project_basemap_data,
                            headers={"X-CSRFToken": csrf_token})



def create_popup_templates(templates_config):
    """
    Creates popup templates based on the provided configuration.
    Args:
        templates_config (List[Dict]): Each dict must include:
            - key: str
            - name: str
            - description: str
            - columns: List[str]
            - title: Optional[str]
            - table_class: Optional[str] (e.g., 'tower-table')
            - color_theme: Optional[str] (e.g., '#4CAF50')

    Returns:
        Dict[str, int]: Map of template key to template ID.
    """

    api_base_url = "http://127.0.0.1:8000/api/v1/"

    print("Creating popup templates...")
    templates = {}
    headers = {"X-CSRFToken": csrf_token}

    for config in templates_config:
        key = config['key']
        name = config['name']
        description = config['description']
        columns = config['columns']
        title = config.get("title", name)
        table_class = config.get("table_class", "popup-table")
        color_theme = config.get("color_theme", "#2196F3")

        # Build the HTML template
        rows_html = "\n".join([
            f"<tr><td><b>{col.replace('_', ' ').title()}</b></td><td>{{{{{col}}}}}</td></tr>"
            for col in columns
        ])

        html_template = f"""<style>
                .{table_class} {{
                    width: 100%;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                }}
                .{table_class} th, .{table_class} td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                    min-width: 120px;
                }}
                .{table_class} th {{
                    background-color: {color_theme};
                    color: white;
                    font-weight: bold;
                }}
                .{table_class} tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .{table_class} tr:hover {{
                    background-color: #ddd;
                }}
                </style>
                <b>{title}</b>
                <table class='{table_class}'>
                {rows_html}
                </table>"""

        field_mappings = {col: col for col in columns}

        template_payload = {
            "name": name,
            "description": description,
            "html_template": html_template,
            "field_mappings": field_mappings,
            "css_styles": "",
            "max_width": 400,
            "max_height": 400,
            "include_zoom_to_feature": True
        }

        # # Check if it exists
        # check_response = session.get(
        #     f"{api_base_url}/popup-templates/",
        #     params={"name": name},
        #     headers= headers
        # )
        # existing = check_response.json()

        # if existing.get('results'):
        #     templates[key] = existing['results'][0]['id']
        #     print(f"Using existing popup template: {name}")
        #     continue

        
        response = session.post(
                f"{api_base_url}/popup-templates/",
                json=template_payload,
                headers=headers
            )
        print(response)
        templates[key] = response.json()['id']
        print(f"Created popup template: {name}")


        return templates


def main():
    authenticate()
    create_project()

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    templates_config = [
    {
        "key": "locations",
        "name": "location Info Popup",
        "description": "Popup showing location data",
        "columns": ["x", "y", "name"],
        "title": "Location Information",
        "color_theme": "#FFFFFF",
        "table_class": "loc-table"
    }
]

    templates = create_popup_templates(templates_config)

    for layer in config:
        process_layer(layer)



    print("All layers processed.")


if __name__ == "__main__":
    main()