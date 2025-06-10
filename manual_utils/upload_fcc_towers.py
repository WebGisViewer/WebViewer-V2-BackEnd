# fcc_towers_upload.py
import os
import json

import numpy as np
import requests
import geopandas as gpd
import pandas as pd
from typing import Dict, List, Optional, Tuple
import random
from shapely.ops import unary_union
import base64
from shapely.geometry import mapping



class FCCTowersProjectUploader:
    """Handles uploading FCC Towers projects to WebGIS V2"""

    def __init__(self, api_base_url: str, access_token: str, test_mode: bool = False):
        self.api_base_url = api_base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        self.file_headers = {
            'Authorization': f'Bearer {access_token}',
        }

        # TEST MODE - limits data uploads
        self.test_mode = test_mode
        self.test_limit = 100

        # Chunk size for uploads
        self.chunk_size = 25000

        # Predefined WISP colors
        self.wisp_colors = {
            "AT&T": "#009FDB",
            "T-Mobile": "#E20074",
            "Verizon": "#E81123",
            "Mediacom Bolt": "#0033A0",
            "Point Broadband": "#F89728",
            "Cloud 9 Wireless": "#6BACE4",
            "Dragonfly Internet": "#FF5733",
            "Rapid Wireless LLC": "#28A745",
            "Wildstar Networks": "#8E44AD"
        }

        # Grid layer color ranges
        self.grid_ranges = {
            "0": {"range": (1, 5), "color": "#e4e4f3"},
            "1": {"range": (5, 10), "color": "#d1d1ea"},
            "2": {"range": (10, 20), "color": "#b3b3e0"},
            "3": {"range": (20, 30), "color": "#8080c5"},
            "4": {"range": (30, 50), "color": "#6d6dbd"},
            "5": {"range": (50, 75), "color": "#4949ac"},
            "6": {"range": (75, 100), "color": "#3737a4"},
            "7": {"range": (100, 50000), "color": "#121293"},
        }

        # Tower company colors
        self.tower_colors = {
            "American Towers": "red",
            "SBA": "purple",
            "Crown Castle": "orange",
            "Other": "blue"
        }

    def create_project(self, project_name: str, state_name: str,
                       center_lat: float, center_lng: float) -> int:
        """Step 1: Create the base project"""
        print(f"Creating project: {project_name}")

        project_data = {
            "name": project_name,
            "description": f"FCC Towers and BEAD Analysis for {state_name}",
            "is_public": False,
            "is_active": True,
            "default_center_lat": center_lat,
            "default_center_lng": center_lng,
            "default_zoom_level": 7,
            "min_zoom": 3,
            "max_zoom": 18,
            "map_controls": {
                "zoomControl": True,
                "attributionControl": False
            }
        }

        response = requests.post(
            f"{self.api_base_url}/projects/",
            json=project_data,
            headers=self.headers
        )
        response.raise_for_status()
        project = response.json()
        print(f"Created project with ID: {project['id']}")
        return project['id']

    def setup_basemaps(self, project_id: int):
        """Step 2: Add basemaps to project"""
        print("Setting up basemaps...")

        # First, clean up any existing basemap associations for this project
        response = requests.get(
            f"{self.api_base_url}/project-basemaps/",
            params={"project_id": project_id},
            headers=self.headers
        )
        response.raise_for_status()
        existing_associations = response.json()

        print(f"Found {len(existing_associations.get('results', []))} existing basemap associations")

        # Delete existing associations
        for assoc in existing_associations.get('results', []):
            try:
                delete_response = requests.delete(
                    f"{self.api_base_url}/project-basemaps/{assoc['id']}/",
                    headers=self.headers
                )
                delete_response.raise_for_status()
                print(f"Removed existing basemap association: {assoc.get('basemap_name', 'Unknown')}")
            except Exception as e:
                print(f"Error removing association: {e}")

        # Now add basemaps fresh
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

        basemap_ids_added = []

        for idx, basemap_config in enumerate(basemaps_to_add):
            # Check if basemap exists
            response = requests.get(
                f"{self.api_base_url}/basemaps/",
                params={"name": basemap_config["name"]},
                headers=self.headers
            )
            response.raise_for_status()
            existing = response.json()

            if existing['results']:
                basemap_id = existing['results'][0]['id']
                print(f"Using existing basemap: {basemap_config['name']} (ID: {basemap_id})")
            else:
                # Create new basemap
                response = requests.post(
                    f"{self.api_base_url}/basemaps/",
                    json=basemap_config,
                    headers=self.headers
                )
                response.raise_for_status()
                basemap_id = response.json()['id']
                print(f"Created basemap: {basemap_config['name']} (ID: {basemap_id})")

            # Add to project - always try to add since we deleted all associations
            project_basemap_data = {
                "project": project_id,  # The POST data uses 'project', not 'project_id'
                "basemap": basemap_id,
                "is_default": idx == 1,  # Make Google Maps default
                "display_order": idx,
                "custom_options": {}
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/project-basemaps/",
                    json=project_basemap_data,
                    headers=self.headers
                )
                response.raise_for_status()
                basemap_ids_added.append(basemap_id)
                print(f"Associated basemap {basemap_config['name']} with project")
            except requests.exceptions.HTTPError as e:
                print(f"\nError associating basemap {basemap_config['name']}: {e}")
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text}")

                # If it's a unique constraint error, it means it's already associated
                if e.response.status_code == 400 and "unique" in e.response.text.lower():
                    print(f"Basemap {basemap_config['name']} seems to be already associated (unique constraint)")
                    basemap_ids_added.append(basemap_id)
                else:
                    # For other errors, try to continue
                    print("Continuing with next basemap...")

        # Verify all basemaps were added
        print(f"\nVerifying basemap associations...")
        response = requests.get(
            f"{self.api_base_url}/project-basemaps/",
            params={"project_id": project_id},
            headers=self.headers
        )
        response.raise_for_status()
        final_associations = response.json()

        print(f"Final count: {len(final_associations.get('results', []))} basemaps associated with project")
        for assoc in final_associations.get('results', []):
            print(f"  - {assoc.get('basemap_name', 'Unknown')} (default: {assoc.get('is_default', False)})")

        if len(final_associations.get('results', [])) < 3:
            print(f"WARNING: Expected 3 basemaps but only {len(final_associations.get('results', []))} are associated!")

        print("Basemaps configured")

    def create_popup_templates(self) -> Dict[str, int]:
        """Step 3: Create popup templates"""
        print("Creating popup templates...")

        templates = {}

        # CBRS popup template for counties
        cbrs_template = {
            "name": "CBRS County Popup",
            "description": "Popup template for county CBRS information",
            "html_template": """<style>
    .cbrs-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
    }
    .cbrs-table th, .cbrs-table td {
        border: 1px solid #ddd;
        padding: 15px;
        text-align: left;
        min-width: 150px;
    }
    .cbrs-table th {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .cbrs-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    .cbrs-table tr:hover {
        background-color: #ddd;
    }
    </style>
    <b>CBRS PAL License Holders</b>
    <table class='cbrs-table'>
      <tr><th>Channel</th><th>County</th><th>Bidder</th></tr>
      {{cbrs_rows}}
    </table>""",
            "field_mappings": {
                "cbrs_rows": "cbrs_data"
            },
            "css_styles": "",
            "max_width": 500,
            "max_height": 400,
            "include_zoom_to_feature": True
        }

        # Tower popup template
        tower_template = {
            "name": "Tower Information Popup",
            "description": "Popup template for FCC tower information",
            "html_template": """<style>
    .tower-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
    }
    .tower-table th, .tower-table td {
        border: 1px solid #ddd;
        padding: 10px;
        text-align: left;
        min-width: 120px;
    }
    .tower-table th {
        background-color: #2196F3;
        color: white;
        font-weight: bold;
    }
    .tower-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    .tower-table tr:hover {
        background-color: #ddd;
    }
    </style>
    <b>FCC Tower Information</b>
    <table class='tower-table'>
        <tr><td><b>Latitude</b></td><td>{{lat}}</td></tr>
        <tr><td><b>Longitude</b></td><td>{{lon}}</td></tr>
        <tr><td><b>County Name</b></td><td>{{county_display}}</td></tr>
        <tr><td><b>Overall Height Above Ground (Meters)</b></td><td>{{overall_height_above_ground}}</td></tr>
        <tr><td><b>Type</b></td><td>{{type_display}}</td></tr>
        <tr><td><b>Owner</b></td><td>{{entity}}</td></tr>
    </table>""",
            "field_mappings": {
                "lat": "lat",
                "lon": "lon",
                "county_display": "county_display",
                "overall_height_above_ground": "overall_height_above_ground",
                "type_display": "type_display",
                "entity": "entity"
            },
            "css_styles": "",
            "max_width": 400,
            "max_height": 400,
            "include_zoom_to_feature": True
        }

        for name, template_data in [("cbrs", cbrs_template), ("tower", tower_template)]:
            check_response = requests.get(
                f"{self.api_base_url}/popup-templates/",
                params={"name": template_data["name"]},
                headers=self.headers
            )
            check_response.raise_for_status()
            existing = check_response.json()

            if existing.get('results'):
                templates[name] = existing['results'][0]['id']
                print(f"Using existing popup template: {template_data['name']}")
                continue

            try:
                response = requests.post(
                    f"{self.api_base_url}/popup-templates/",
                    json=template_data,
                    headers=self.headers
                )
                response.raise_for_status()
                templates[name] = response.json()['id']
                print(f"Created popup template: {template_data['name']}")
            except requests.exceptions.HTTPError as e:
                print(f"Error creating popup template: {e}")
                print(f"Response content: {e.response.text}")
                print(f"Request data: {json.dumps(template_data, indent=2)}")
                raise

        return templates

    def create_layer_function(self) -> int:
        """Create a clustering function for BEAD locations"""
        print("Creating clustering function...")

        function_name = "BEAD Location Clustering"

        check_response = requests.get(
            f"{self.api_base_url}/layer-functions/",
            params={"name": function_name},
            headers=self.headers
        )
        check_response.raise_for_status()
        existing = check_response.json()

        if existing.get('results'):
            function_id = existing['results'][0]['id']
            print(f"Using existing clustering function with ID: {function_id}")
            return function_id

        function_data = {
            "name": function_name,
            "description": "Clusters BEAD eligible locations",
            "function_type": "clustering",
            "function_config": {
                "disableClusteringAtZoom": 11,
                "showCoverageOnHover": False,
                "zoomToBoundsOnClick": True,
                "spiderfyOnMaxZoom": True,
                "removeOutsideVisibleBounds": True
            }
        }

        try:
            response = requests.post(
                f"{self.api_base_url}/layer-functions/",
                json=function_data,
                headers=self.headers
            )
            response.raise_for_status()
            function_id = response.json()['id']
            print(f"Created clustering function with ID: {function_id}")
            return function_id
        except requests.exceptions.HTTPError as e:
            print(f"Error creating layer function: {e}")
            print(f"Response content: {e.response.text}")
            print(f"Request data: {json.dumps(function_data, indent=2)}")

            if e.response.status_code == 400 and "unique" in e.response.text.lower():
                print("Trying to find existing function due to unique constraint...")
                search_response = requests.get(
                    f"{self.api_base_url}/layer-functions/",
                    params={"function_type": "clustering"},
                    headers=self.headers
                )
                search_response.raise_for_status()
                functions = search_response.json().get('results', [])

                for func in functions:
                    if "BEAD" in func.get('name', ''):
                        print(f"Found existing BEAD clustering function with ID: {func['id']}")
                        return func['id']

            raise

    def create_layer_groups(self, project_id: int) -> Dict[str, int]:
        """Step 4: Create layer groups"""
        print("Creating layer groups...")

        groups = {
            "administrative": {
                "name": "Administrative Boundaries",
                "display_order": 1,
                "is_visible_by_default": True,
                "is_expanded_by_default": True
            },
            "infrastructure": {
                "name": "Infrastructure",
                "display_order": 2,
                "is_visible_by_default": True,
                "is_expanded_by_default": True
            },
            "coverage": {
                "name": "Coverage Analysis",
                "display_order": 3,
                "is_visible_by_default": False,
                "is_expanded_by_default": False
            },
            "analysis": {
                "name": "Grid Analysis",
                "display_order": 4,
                "is_visible_by_default": False,
                "is_expanded_by_default": False
            }
        }

        group_ids = {}
        for key, group_data in groups.items():
            group_data["project"] = project_id

            response = requests.post(
                f"{self.api_base_url}/layer-groups/",
                json=group_data,
                headers=self.headers
            )
            response.raise_for_status()
            group_ids[key] = response.json()['id']
            print(f"Created layer group: {group_data['name']}")

        return group_ids

    def get_or_create_layer_type(self, type_name: str) -> int:
        """Get existing layer type or create if needed"""
        # First, let's see what layer types exist
        response = requests.get(
            f"{self.api_base_url}/layer-types/",
            headers=self.headers
        )
        response.raise_for_status()
        all_types = response.json()

        print(f"Available layer types: {[t['type_name'] for t in all_types.get('results', [])]}")

        # Try to find by exact name
        response = requests.get(
            f"{self.api_base_url}/layer-types/",
            params={"type_name": type_name},
            headers=self.headers
        )
        response.raise_for_status()
        existing = response.json()

        if existing['results']:
            return existing['results'][0]['id']

        # If not found, create new layer type
        layer_type_data = {
            "type_name": type_name,
            "description": f"{type_name} features",
            "is_system": False
        }

        try:
            response = requests.post(
                f"{self.api_base_url}/layer-types/",
                json=layer_type_data,
                headers=self.headers
            )
            response.raise_for_status()
            created_type = response.json()
            print(f"Created new layer type: {type_name} (ID: {created_type['id']})")
            return created_type['id']
        except requests.exceptions.HTTPError as e:
            print(f"Error creating layer type {type_name}: {e}")
            print(f"Response: {e.response.text}")

            # If we can't create, fall back to Default-Line if it exists
            for layer_type in all_types.get('results', []):
                if 'default' in layer_type['type_name'].lower():
                    print(f"Falling back to {layer_type['type_name']} (ID: {layer_type['id']})")
                    return layer_type['id']

            raise
    def create_state_layer(self, group_id: int, state_file: str) -> int:
        """Create a state outline layer"""
        print("Creating state outline layer...")

        layer_type_id = self.get_or_create_layer_type("Polygon")

        layer_data = {
            "project_layer_group": group_id,
            "layer_type": layer_type_id,
            "name": "State Outline",
            "description": "State boundary",
            "style": {
                "fillColor": "none",
                "color": "red",
                "weight": 2,
                "fillOpacity": 0
            },
            "z_index": 1,
            "is_visible_by_default": True
        }

        response = requests.post(
            f"{self.api_base_url}/layers/",
            json=layer_data,
            headers=self.headers
        )
        response.raise_for_status()
        layer_id = response.json()['id']

        self.upload_geometry_file(layer_id, state_file)

        return layer_id

    def create_county_layer(self, group_id: int, county_file: str,
                            popup_template_id: int, cbrs_file: str) -> int:
        """Create a county outline layer with CBRS data"""
        print("Creating county outline layer...")

        layer_type_id = self.get_or_create_layer_type("Polygon")

        layer_data = {
            "project_layer_group": group_id,
            "layer_type": layer_type_id,
            "name": "County Outline",
            "description": "County boundaries with CBRS information",
            "style": {
                "fillColor": "none",
                "color": "blue",
                "weight": 1,
                "fillOpacity": 0
            },
            "z_index": 2,
            "is_visible_by_default": True,
            "popup_template": popup_template_id
        }

        print(f"Creating county layer with popup template ID: {popup_template_id}")

        response = requests.post(
            f"{self.api_base_url}/layers/",
            json=layer_data,
            headers=self.headers
        )
        response.raise_for_status()
        layer_id = response.json()['id']

        self.upload_county_data_with_cbrs(layer_id, county_file, cbrs_file)

        return layer_id

    def create_bead_locations_layer(self, group_id: int, bead_file: str,
                                    clustering_function_id: int) -> int:
        """Create BEAD eligible locations layer with clustering"""
        print("Creating BEAD eligible locations layer...")

        layer_type_id = self.get_or_create_layer_type("Point")

        layer_data = {
            "project_layer_group": group_id,
            "layer_type": layer_type_id,
            "name": "BEAD Eligible Locations",
            "description": "Locations eligible for BEAD funding",
            "style": {
                "radius": 4,
                "color": "black",
                "fillColor": "#01fbff",
                "fillOpacity": 1,
                "weight": 1
            },
            "z_index": 10,
            "is_visible_by_default": True,
            "enable_clustering": True,
            "clustering_options": {
                "disableClusteringAtZoom": 11,
                "showCoverageOnHover": False,
                "zoomToBoundsOnClick": True,
                "spiderfyOnMaxZoom": True
            }
        }

        response = requests.post(
            f"{self.api_base_url}/layers/",
            json=layer_data,
            headers=self.headers
        )
        response.raise_for_status()
        layer_id = response.json()['id']

        # Add a clustering function
        function_data = {
            "project_layer": layer_id,
            "layer_function": clustering_function_id,
            "enabled": True,
            "priority": 100
        }

        response = requests.post(
            f"{self.api_base_url}/project-layer-functions/",
            json=function_data,
            headers=self.headers
        )
        response.raise_for_status()

        self.upload_geometry_file(layer_id, bead_file)

        return layer_id

    def create_grid_layers(self, group_id: int, grid_file: str) -> List[int]:
        """Create grid analysis layers"""
        print("Creating grid analysis layers...")

        layer_type_id = self.get_or_create_layer_type("Polygon")

        grid_gdf = gpd.read_file(grid_file).set_crs("EPSG:4326", allow_override=True)
        print(grid_gdf.head())
        if self.test_mode:
            original_count = len(grid_gdf)
            grid_gdf = grid_gdf.head(self.test_limit * 2)
            print(f"TEST MODE: Limiting grid from {original_count} to {len(grid_gdf)} cells")

        layer_ids = []
        created_count = 0

        for key, config in self.grid_ranges.items():
            rng_min, rng_max = config["range"]
            color = config["color"]

            subset = grid_gdf[
                (grid_gdf["point_count"] >= rng_min) &
                (grid_gdf["point_count"] < rng_max)
                ]

            if len(subset) == 0:
                print(f"  No cells found for range {rng_min}-{rng_max}")
                continue

            print(f"  Found {len(subset)} cells for range {rng_min}-{rng_max}")

            if rng_min == 100:
                layer_name = f"Grid Layer ({rng_min}+ Locations)"
            else:
                layer_name = f"Grid Layer ({rng_min}-{rng_max} Locations)"

            try:
                layer_data = {
                    "project_layer_group": group_id,
                    "layer_type": layer_type_id,
                    "name": layer_name,
                    "description": f"Grid cells with {rng_min}-{rng_max} locations",
                    "style": {
                        "fillColor": color,
                        "color": color,
                        "weight": 1,
                        "fillOpacity": 0.6
                    },
                    "z_index": 5 + int(key),
                    "is_visible_by_default": False
                }

                response = requests.post(
                    f"{self.api_base_url}/layers/",
                    json=layer_data,
                    headers=self.headers
                )
                response.raise_for_status()
                layer_id = response.json()['id']

                dissolved_geo = unary_union(subset["geometry"])
                dissolved_gdf = gpd.GeoDataFrame(
                    geometry=[dissolved_geo],
                    crs="EPSG:4326"
                )

                features = []
                for _, row in dissolved_gdf.iterrows():
                    features.append({
                        "type": "Feature",
                        "geometry": mapping(row.geometry),
                        "properties": {"point_count_range": f"{rng_min}-{rng_max}"}
                    })

                geojson_data = {
                    "type": "FeatureCollection",
                    "features": features
                }

                response = requests.post(
                    f"{self.api_base_url}/layers/{layer_id}/import_geojson/",
                    json=geojson_data,
                    headers=self.headers
                )
                response.raise_for_status()

                layer_ids.append(layer_id)
                created_count += 1
                print(f"Created grid layer: {layer_name}")

            except Exception as e:
                print(f"ERROR creating grid layer {layer_name}: {e}")
                if hasattr(e, 'response'):
                    print(f"Response: {e.response.text}")

        print(f"Total grid layers created: {created_count}")
        return layer_ids

    def create_wisp_layers(self, group_id: int, wisp_folder: str) -> List[int]:
        """Create WISP coverage layers"""
        print("Creating WISP layers...")

        layer_type_id = self.get_or_create_layer_type("Polygon")
        layer_ids = []

        if not os.path.isdir(wisp_folder):
            print("WISP folder not found")
            return layer_ids

        for file in os.listdir(wisp_folder):
            if file.endswith(".sqlite"):
                file_path = os.path.join(wisp_folder, file)
                wisp_name = os.path.splitext(file)[0]

                color = self.get_wisp_color(wisp_name)

                layer_data = {
                    "project_layer_group": group_id,
                    "layer_type": layer_type_id,
                    "name": f"WISP - {wisp_name}",
                    "description": f"Coverage area for {wisp_name}",
                    "style": {
                        "fillColor": color,
                        "color": color,
                        "weight": 1,
                        "fillOpacity": 0.6
                    },
                    "z_index": 20,
                    "is_visible_by_default": False
                }

                response = requests.post(
                    f"{self.api_base_url}/layers/",
                    json=layer_data,
                    headers=self.headers
                )
                response.raise_for_status()
                layer_id = response.json()['id']

                self.upload_geometry_file(layer_id, file_path)

                layer_ids.append(layer_id)
                print(f"Created WISP layer: {wisp_name}")

        return layer_ids

    def create_tower_layers(self, group_id: int, antenna_file: str,
                            popup_template_id: int) -> List[int]:
        """Create antenna tower layers by company"""
        print("Creating antenna tower layers...")

        layer_type_id = self.get_or_create_layer_type("Point")

        antenna_gdf = gpd.read_file(antenna_file).set_crs("EPSG:4326", allow_override=True)

        if self.test_mode:
            original_count = len(antenna_gdf)
            antenna_gdf = antenna_gdf.head(self.test_limit * 4)  # Since we split by company
            print(f"TEST MODE: Limiting towers from {original_count} to {len(antenna_gdf)}")

        layer_ids = []
        for company, color in self.tower_colors.items():
            if company == "Other":
                company_data = antenna_gdf[antenna_gdf['grouped_entity'] == company]
            else:
                company_data = antenna_gdf[antenna_gdf['grouped_entity'] == company.replace(" Towers", "")]

            if len(company_data) == 0:
                continue

            layer_data = {
                "project_layer_group": group_id,
                "layer_type": layer_type_id,
                "name": f"Antenna Locations - {company}",
                "description": f"Tower locations owned by {company}",
                "style": {
                    "color": color,
                    "fillColor": color
                },
                "marker_type": "icon",
                "marker_options": {
                    "icon": "wifi",
                    "prefix": "fa",
                    "color": color,
                    "iconColor": "white"
                },
                "z_index": 30,
                "is_visible_by_default": False,
                "popup_template": popup_template_id
            }

            print(f"Creating tower layer for {company} with color {color} and popup template {popup_template_id}")

            response = requests.post(
                f"{self.api_base_url}/layers/",
                json=layer_data,
                headers=self.headers
            )
            response.raise_for_status()
            layer_id = response.json()['id']

            features = []
            for _, row in company_data.iterrows():
                def safe_value(val, default="N/A"):
                    if pd.isna(val):
                        return default
                    return str(val)

                properties = {
                    "lat": safe_value(row.get("lat")),
                    "lon": safe_value(row.get("lon")),
                    "county_display": f"{safe_value(row.get('county_name'))} ({safe_value(row.get('state_fips'))}{safe_value(row.get('county_fips'))})",
                    "overall_height_above_ground": safe_value(row.get("overall_height_above_ground")),
                    "type_display": f"{safe_value(row.get('english_type'))} ({safe_value(row.get('structure_type'))})",
                    "entity": safe_value(row.get('entity'))
                }

                features.append({
                    "type": "Feature",
                    "geometry": mapping(row.geometry),
                    "properties": properties
                })

            chunk_size = 500
            for i in range(0, len(features), chunk_size):
                chunk = features[i:i + chunk_size]

                geojson_data = {
                    "type": "FeatureCollection",
                    "features": chunk
                }

                response = requests.post(
                    f"{self.api_base_url}/layers/{layer_id}/import_geojson/",
                    json=geojson_data,
                    headers=self.headers
                )
                response.raise_for_status()

            layer_ids.append(layer_id)
            print(f"Created tower layer: {company} with {len(features)} features")

        return layer_ids

    def upload_geometry_file(self, layer_id: int, file_path: str):
        """Upload geometry file to layer"""
        gdf = gpd.read_file(file_path).set_crs("EPSG:4326", allow_override=True)

        if self.test_mode:
            original_count = len(gdf)
            gdf = gdf.head(self.test_limit)
            print(f"TEST MODE: Limiting upload from {original_count} to {len(gdf)} features")

        features = []
        for _, row in gdf.iterrows():
            properties = {}
            for key, value in row.drop('geometry').items():
                if pd.isna(value):
                    properties[key] = None
                elif isinstance(value, (float, np.floating)):
                    if np.isnan(value) or np.isinf(value):
                        properties[key] = None
                    else:
                        properties[key] = float(value)
                elif isinstance(value, (int, np.integer)):
                    properties[key] = int(value)
                else:
                    properties[key] = str(value) if value is not None else None

            features.append({
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": properties
            })

        chunk_size = self.chunk_size

        total_uploaded = 0
        for i in range(0, len(features), chunk_size):
            chunk = features[i:i + chunk_size]

            geojson_data = {
                "type": "FeatureCollection",
                "features": chunk
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/layers/{layer_id}/import_geojson/",
                    json=geojson_data,
                    headers=self.headers
                )
                response.raise_for_status()
                total_uploaded += len(chunk)
                print(f"Uploaded batch {i // chunk_size + 1}: {len(chunk)} features")
            except requests.exceptions.RequestException as e:
                print(f"Error uploading batch {i // chunk_size + 1}: {e}")
                if hasattr(e, 'response') and e.response:
                    print(f"Response content: {e.response.text}")
                raise

        print(f"Total uploaded: {total_uploaded} features to layer {layer_id}")

    def upload_county_data_with_cbrs(self, layer_id: int, county_file: str, cbrs_file: str):
        """Upload county data with CBRS information"""
        county_gdf = gpd.read_file(county_file).set_crs("EPSG:4326", allow_override=True)

        cbrs_df = pd.read_excel(cbrs_file, usecols=["Channel", "county_name", "bidder"])
        cbrs_data = cbrs_df.groupby("county_name", group_keys=False).apply(
            lambda x: x.to_dict(orient="records")
        ).to_dict()

        features = []
        for _, row in county_gdf.iterrows():
            county_name = row.get("name", "Unknown County")

            cbrs_info = cbrs_data.get(county_name, [])

            cbrs_rows = ""
            for entry in cbrs_info:
                cbrs_rows += (
                    f"<tr>"
                    f"<td>{entry['Channel']}</td>"
                    f"<td>{entry['county_name']}</td>"
                    f"<td>{entry['bidder']}</td>"
                    f"</tr>"
                )

            properties = {}
            for key, value in row.drop('geometry').items():
                if pd.isna(value):
                    properties[key] = None
                elif isinstance(value, (float, np.floating)):
                    if np.isnan(value) or np.isinf(value):
                        properties[key] = None
                    else:
                        properties[key] = float(value)
                elif isinstance(value, (int, np.integer)):
                    properties[key] = int(value)
                else:
                    properties[key] = str(value) if value is not None else None

            properties['cbrs_data'] = cbrs_rows
            properties['county_name'] = county_name

            features.append({
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": properties
            })

        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }

        response = requests.post(
            f"{self.api_base_url}/layers/{layer_id}/import_geojson/",
            json=geojson_data,
            headers=self.headers
        )
        response.raise_for_status()
        print(f"Uploaded {len(features)} counties with CBRS data")

    def get_wisp_color(self, wisp_name: str) -> str:
        """Get color for WISP based on name"""
        for key in self.wisp_colors:
            if key.lower() in wisp_name.lower().strip():
                return self.wisp_colors[key]
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def upload_fcc_towers_project(self,
                                  project_name: str,
                                  state_name: str,
                                  base_folder: str,
                                  antenna_file: str,
                                  cbrs_file: str,
                                  center_lat: float,
                                  center_lng: float):
        """Main method to upload complete FCC Towers project"""

        print(f"\n=== Starting FCC Towers Project Upload for {state_name} ===\n")

        state_file = os.path.join(base_folder, f"{state_name} State Outline.sqlite")
        county_file = os.path.join(base_folder, f"{state_name} County Outline.sqlite")
        bead_file = os.path.join(base_folder, f"{state_name} BEAD Eligible Locations.sqlite")
        grid_file = os.path.join(base_folder, f"{state_name} BEAD Grid Analysis Layer.sqlite")

        wisp_folder = ""
        if os.path.exists(os.path.join(base_folder, f"{state_name} WISPs Hex Dissolved")):
            wisp_folder = os.path.join(base_folder, f"{state_name} WISPs Hex Dissolved")
        elif os.path.exists(os.path.join(base_folder, f"{state_name} WISPs Dissolved")):
            wisp_folder = os.path.join(base_folder, f"{state_name} WISPs Dissolved")

        # Step 1: Create project
        project_id = self.create_project(project_name, state_name, center_lat, center_lng)

        # Step 2: Setup basemaps
        self.setup_basemaps(project_id)

        # Step 3: Create popup templates
        popup_templates = self.create_popup_templates()

        # Step 4: Create clustering function
        clustering_function_id = self.create_layer_function()

        # Step 5: Create layer groups
        layer_groups = self.create_layer_groups(project_id)

        # Step 6: Create layers
        # Administrative layers
        self.create_state_layer(layer_groups["administrative"], state_file)
        self.create_county_layer(
            layer_groups["administrative"],
            county_file,
            popup_templates["cbrs"],
            cbrs_file
        )

        # Infrastructure layers
        self.create_bead_locations_layer(
            layer_groups["infrastructure"],
            bead_file,
            clustering_function_id
        )

        self.create_tower_layers(
            layer_groups["infrastructure"],
            antenna_file,
            popup_templates["tower"]
        )

        # Analysis layers
        self.create_grid_layers(layer_groups["analysis"], grid_file)

        # Coverage layers
        if wisp_folder:
            self.create_wisp_layers(layer_groups["coverage"], wisp_folder)

        print(f"\n=== Project Upload Complete! ===")
        print(f"Project ID: {project_id}")
        print(f"Access the project constructor at: {self.api_base_url}/constructor/{project_id}/")

        print("\n=== Verification ===")

        # Check basemaps
        response = requests.get(
            f"{self.api_base_url}/project-basemaps/",
            params={"project_id": project_id},
            headers=self.headers
        )
        if response.ok:
            basemaps = response.json()
            print(f"Basemaps: {basemaps.get('count', 0)}")

        # Check layers by group
        for group_name, group_id in layer_groups.items():
            response = requests.get(
                f"{self.api_base_url}/layers/",
                params={"project_layer_group": group_id},
                headers=self.headers
            )
            if response.ok:
                layers = response.json()
                print(f"{group_name}: {layers.get('count', 0)} layers")

        return project_id

    def debug_api_call(self, method: str, url: str, **kwargs):
        """Debug helper to log API calls"""
        print(f"\n=== API Call Debug ===")
        print(f"Method: {method}")
        print(f"URL: {url}")
        if 'json' in kwargs:
            print(f"JSON Data: {json.dumps(kwargs['json'], indent=2)}")
        if 'params' in kwargs:
            print(f"Query Params: {kwargs['params']}")
        print("=" * 20)

        response = requests.request(method, url, **kwargs)

        print(f"Response Status: {response.status_code}")
        if not response.ok:
            print(f"Response Body: {response.text}")
        print("=" * 20 + "\n")

        return response

    def test_connection(self):
        """Test API connection and authentication"""
        print("Testing API connection...")

        try:
            response = requests.get(
                f"{self.api_base_url}/users/me/",
                headers=self.headers
            )
            response.raise_for_status()
            user = response.json()
            print(f"Connected as: {user['username']} (Admin: {user.get('is_admin', False)})")
            return True
        except requests.exceptions.HTTPError as e:
            print(f"Authentication failed: {e}")
            print(f"Response: {e.response.text}")
            return False

if __name__ == "__main__":

    uploader = FCCTowersProjectUploader(
        api_base_url="http://127.0.0.1:8000/api/v1",
        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQ5NTM0MTk2LCJpYXQiOjE3NDk1MzA1OTYsImp0aSI6IjEwNGU3NzU4MDRiOTRhMzdiNDliMjFjYzdhZmEyOTMzIiwidXNlcl9pZCI6MX0.0sFSujslyf8ULXVRJE3_rTzrzCGYUxJkXY_kSEyAYr4",
        test_mode=True
    )

    print("=" * 50)
    print("RUNNING IN TEST MODE - Limited data upload")
    print("=" * 50)

    project_id = uploader.upload_fcc_towers_project(
        project_name="Ohio FCC Towers Analysis - TEST",
        state_name="Ohio",
        base_folder=r"C:\Users\meloy\Desktop\Ohio New",
        antenna_file=r"C:\Users\meloy\PycharmProjects\MapGenerationTool\OhioTowers_2.sqlite",
        cbrs_file=r"C:\Users\meloy\Documents\CBRS-Ohio.xlsx",
        center_lat=40.4173,
        center_lng=-82.9071
    )

    print("\n" + "=" * 50)
    print("TEST MODE COMPLETE")
    print("To run full upload, set test_mode=False")
    print("=" * 50)