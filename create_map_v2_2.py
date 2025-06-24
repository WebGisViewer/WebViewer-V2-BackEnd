import os
import json
import requests
from bs4 import BeautifulSoup

"""
we should work on 

        1. popups (code that adds a popup template and assigns it to a layer is written but didn't work)
        2. center coordinates, when a user opens the map, where it should display -- center_coordinates_func(layer)
        3. when a layer has too many features it gives an error
        4. add options for openstreet map, white screen and google satellite 

"""


"""
 {
        "filename": "Clallam County-19 Access Fiber Miles.sqlite",
        "layer_name": "Clallam County-19 Access Fiber Miles",
        "layer_type_id": 7,
        "style": {
  "color": "black"
},
        "group": "Locations and Road",
        "source_crs": "EPSG:4326",
        "target_crs": "EPSG:4326"
    },
"""
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "adminuser"
PASSWORD = "levon"

FOLDER_PATH = "/Users/levon/Desktop/WebGIS/WebViewer-V2-BackEnd/Test_Project"  # Your folder path here
CONFIG_FILE = os.path.join(FOLDER_PATH, "layer_config.json")
PROJECT_NAME = "Callam PRJ with Custom Styles Uploaded with popup2"


# --- Load configuration ---
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

# --- Setup session and login ---
session = requests.Session()
login_page = session.get(f"{BASE_URL}/admin/login/")
csrf_token = BeautifulSoup(login_page.text, "html.parser").find("input", attrs={"name": "csrfmiddlewaretoken"}).get("value")

login_data = {
    "username": USERNAME,
    "password": PASSWORD,
    "csrfmiddlewaretoken": csrf_token
}
session.post(f"{BASE_URL}/admin/login/", data=login_data, headers={"Referer": f"{BASE_URL}/admin/login/"})
csrf_token = session.cookies.get("csrftoken")


project_payload = {
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


headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/api/v1/projects/"}
response = session.post(f"{BASE_URL}/api/v1/projects/", json=project_payload, headers=headers)
PROJECT_ID = response.json()["id"]
print("Project created:", PROJECT_ID)


LAYER_GROUPS_URL = f"{BASE_URL}/api/v1/layer-groups/"


group_cache = {}

def get_or_create_group(group_name):
    if group_name in group_cache:
        return group_cache[group_name]
    payload = {
        "name": group_name,
        "project": PROJECT_ID,
        "display_order": 1,
        "is_visible_by_default": True,
        "is_expanded_by_default": False
    }
    resp = session.post(f"{BASE_URL}/api/v1/layer-groups/", json=payload, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})
    group_id = resp.json()["id"]
    group_cache[group_name] = group_id
    print(f"Group '{group_name}' created with ID: {group_id}")
    return group_id

for layer in config:
    file_path = os.path.join(FOLDER_PATH, layer["filename"])
    print(f"Processing file: {layer['filename']}")

    upload_resp = session.post(
        f"{BASE_URL}/api/v1/upload/",
        headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL},
        files={"file": open(file_path, "rb")}
    )

    if upload_resp.status_code != 200:
        print(f"Upload failed for {layer['filename']}")
        continue

    upload_data = upload_resp.json()
    group_id = get_or_create_group(layer["group"])

    complete_payload = {
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
        "popup_template_id" : 1
    }

    response = session.post(
        f"{BASE_URL}/api/v1/complete_upload/",
        json=complete_payload,
        headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL}
    )

    if response.status_code == 200:
        layer_id = response.json()["layer_id"]
        print(f"Layer '{layer['layer_name']}' uploaded with ID {layer_id}")
    else:
        print(f"Failed to complete upload for {layer['filename']}")
        continue
    style_id = layer['style_id']
    print("layer is :",layer)

    #custom style upload 
    if "style" in layer.keys():

        # Create the style first
        style_payload = {
            "name": f"Style for layer {layer_id}",
            "description": f"Auto-generated style for Location layer new",
            "style_type": "point",  # assuming vector; you can make this dynamic
            "style_definition": layer["style"],
            "is_system": False
        }

        style_create_resp = session.post(
            f"{BASE_URL}/api/v1/styles/",
            json=style_payload,
            headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL}
        )
        print(style_create_resp.status_code)

        if style_create_resp.status_code == 201:
            style_id = style_create_resp.json()["id"]

    #apply style
    style_url = f"{BASE_URL}/api/v1/styles/{style_id}/apply_to_layer/"
    apply_resp = session.post(style_url, json={"layer_id": layer_id}, headers={"X-CSRFToken": csrf_token, "Referer": BASE_URL})

    if apply_resp.status_code == 200:

        print(f"Style {layer['style_id']} applied to layer {layer_id}")

    else:
        print(f"Failed to apply style for layer {layer_id}")


print("All layers processed.")