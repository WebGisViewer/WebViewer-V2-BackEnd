import os
import json
import requests
from bs4 import BeautifulSoup


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
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/api/v1/projects/"}
    resp = session.post(f"{BASE_URL}/api/v1/projects/", json=payload, headers=headers)
    PROJECT_ID = resp.json()["id"]
    print("Project created:", PROJECT_ID)


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
        "popup_template_id": 1  # Can be dynamically inserted here
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


def main():
    authenticate()
    create_project()

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    for layer in config:
        process_layer(layer)

    print("All layers processed.")


if __name__ == "__main__":
    main()