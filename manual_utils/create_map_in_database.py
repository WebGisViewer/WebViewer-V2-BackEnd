# create_map_in_database.py
import os
import geopandas as gpd
import json
import random
import pandas as pd
from shapely.ops import unary_union
from shapely.geometry import mapping, shape, Point
from geoalchemy2.shape import from_shape
from geoalchemy2 import Geometry  # This is the correct import for column type
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, MetaData, \
    Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import argparse

# Database connection parameters - this will be modifiable via function arguments
DATABASE_URL = "postgresql://postgresqlwireless2020:software2020!!@wirelesspostgresqlflexible.postgres.database.azure.com/wiroidb2"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# Define models matching your database tables
class ViewerProjects(Base):
    __tablename__ = 'wiroi_viewer_projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class LayerGroups(Base):
    __tablename__ = 'wiroi_layer_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('wiroi_viewer_projects.id'), nullable=False)
    group_name = Column(String(100), nullable=False)
    display_order = Column(Integer, default=0)
    is_visible_by_default = Column(Boolean, default=True)


class Layers(Base):
    
    __tablename__ = 'wiroi_layers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_group_id = Column(Integer, ForeignKey('wiroi_layer_groups.id'), nullable=False)
    layer_name = Column(String(100), nullable=False)
    layer_type = Column(String(20), nullable=False)
    is_visible_by_default = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    style_config = Column(Text, nullable=True)


class LayerData(Base):
    __tablename__ = 'wiroi_layer_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('wiroi_layers.id'), nullable=False)
    # Corrected: Use Geometry type for the column, not WKBElement
    geometry = Column(Geometry('GEOMETRY', srid=4326))
    properties = Column(JSONB, nullable=True)
    feature_id = Column(String(100), nullable=True)


def get_wisp_color(wisp_name):
    """Returns a predefined color for well-known WISP providers or assigns a random color."""
    wisp_colors = {
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

    for key in wisp_colors:
        if key.lower() in wisp_name.lower().strip():
            print(f'Found {key} for {wisp_name} after comparing {key.lower()} and {wisp_name.lower()}')
            return wisp_colors[key]

    print('did not find a match for ', wisp_name)
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def create_map_in_database(base_folder, state_name, wisp_folder='', state_outline_file='',
                           county_outline_file='', bead_eligible_locations_file='',
                           grid_analysis_layer_file='', db_url=None):
    """
    Create map data in the database instead of an HTML file.
    Standalone version without requiring Flask application context.

    Parameters:
    -----------
    base_folder : str
        Base folder containing map data
    state_name : str
        Name of the state
    wisp_folder : str, optional
        Folder containing WISP data. If not provided, will look in standard locations
    state_outline_file : str, optional
        Path to state outline file. If not provided, will look in standard location
    county_outline_file : str, optional
        Path to county outline file. If not provided, will look in standard location
    bead_eligible_locations_file : str, optional
        Path to BEAD eligible locations file. If not provided, will look in standard location
    grid_analysis_layer_file : str, optional
        Path to grid analysis layer file. If not provided, will look in standard location
    db_url : str, optional
        Database connection URL. If not provided, uses the default
    """
    global engine, Session

    # Update database connection if a custom URL is provided
    if db_url is not None:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)

    print(f"Creating map data for {state_name} in the database...")

    # Default folder paths for the different files, if not provided
    if not wisp_folder:
        if os.path.exists(os.path.join(base_folder, f"{state_name} WISPs Hex Dissolved")):
            wisp_folder = os.path.join(base_folder, f"{state_name} WISPs Hex Dissolved")
        elif os.path.exists(os.path.join(base_folder, f"{state_name} WISPs Dissolved")):
            wisp_folder = os.path.join(base_folder, f"{state_name} WISPs Dissolved")
    if not state_outline_file:
        state_outline_file = os.path.join(base_folder, f"{state_name} State Outline.sqlite")
    if not county_outline_file:
        county_outline_file = os.path.join(base_folder, f"{state_name} County Outline.sqlite")
    if not bead_eligible_locations_file:
        bead_eligible_locations_file = os.path.join(base_folder, f"{state_name} BEAD Eligible Locations.sqlite")
    if not grid_analysis_layer_file:
        grid_analysis_layer_file = os.path.join(base_folder, f"{state_name} BEAD Grid Analysis Layer.sqlite")

    # Create a session
    session = Session()

    try:
        # Check if project already exists
        project = session.query(ViewerProjects).filter_by(project_name=state_name).first()
        if not project:
            project = ViewerProjects(
                project_name=state_name,
                description=f"Map data for {state_name} state"
            )
            session.add(project)
            session.commit()
            print(f"Created new project for {state_name} with ID {project.id}")
        else:
            print(f"Using existing project for {state_name} with ID {project.id}")

        # Create or get layer groups
        # 1. Base Layers
        base_group = session.query(LayerGroups).filter_by(project_id=project.id, group_name="Base Layers").first()
        if not base_group:
            base_group = LayerGroups(
                project_id=project.id,
                group_name="Base Layers",
                display_order=0,
                is_visible_by_default=True
            )
            session.add(base_group)

        # 2. Administrative Boundaries
        admin_group = session.query(LayerGroups).filter_by(project_id=project.id,
                                                           group_name="Administrative Boundaries").first()
        if not admin_group:
            admin_group = LayerGroups(
                project_id=project.id,
                group_name="Administrative Boundaries",
                display_order=1,
                is_visible_by_default=True
            )
            session.add(admin_group)

        # 3. WISP Coverage
        wisp_group = session.query(LayerGroups).filter_by(project_id=project.id, group_name="WISP Coverage").first()
        if not wisp_group:
            wisp_group = LayerGroups(
                project_id=project.id,
                group_name="WISP Coverage",
                display_order=2,
                is_visible_by_default=False
            )
            session.add(wisp_group)

        # 4. BEAD Data
        bead_group = session.query(LayerGroups).filter_by(project_id=project.id, group_name="BEAD Data").first()
        if not bead_group:
            bead_group = LayerGroups(
                project_id=project.id,
                group_name="BEAD Data",
                display_order=3,
                is_visible_by_default=True
            )
            session.add(bead_group)

        session.commit()

        # Process State Outline
        if os.path.exists(state_outline_file):
            print(f"Processing state outline from {state_outline_file}")
            state_outline = gpd.read_file(state_outline_file)[['geometry']].set_crs("EPSG:4326")

            # Create or get layer
            state_layer = session.query(Layers).filter_by(layer_group_id=admin_group.id,
                                                          layer_name="State Outline").first()
            if not state_layer:
                state_layer = Layers(
                    layer_group_id=admin_group.id,
                    layer_name="State Outline",
                    layer_type="polygon",
                    display_order=0,
                    is_visible_by_default=True,
                    style_config=json.dumps({
                        "fillColor": "none",
                        "color": "red",
                        "weight": 2,
                        "fillOpacity": 0
                    })
                )
                session.add(state_layer)
                session.commit()

            # Add state outline features if they don't exist yet
            if session.query(func.count(LayerData.id)).filter_by(layer_id=state_layer.id).scalar() == 0:
                for idx, row in state_outline.iterrows():
                    layer_data = LayerData(
                        layer_id=state_layer.id,
                        geometry=from_shape(row.geometry, srid=4326),
                        properties=json.dumps({}),
                        feature_id=f"state_outline_{idx}"
                    )
                    session.add(layer_data)
                session.commit()
                print(f"Added state outline geometry to database")

        # Process County Outline
        if os.path.exists(county_outline_file):
            print(f"Processing county outlines from {county_outline_file}")
            county_outline = gpd.read_file(county_outline_file).set_crs("EPSG:4326")

            # Create or get layer
            county_layer = session.query(Layers).filter_by(layer_group_id=admin_group.id,
                                                           layer_name="County Outlines").first()
            if not county_layer:
                county_layer = Layers(
                    layer_group_id=admin_group.id,
                    layer_name="County Outlines",
                    layer_type="polygon",
                    display_order=1,
                    is_visible_by_default=True,
                    style_config=json.dumps({
                        "fillColor": "none",
                        "color": "blue",
                        "weight": 1,
                        "fillOpacity": 0
                    })
                )
                session.add(county_layer)
                session.commit()

            # Add county outline features if they don't exist yet
            if session.query(func.count(LayerData.id)).filter_by(layer_id=county_layer.id).scalar() == 0:
                county_labels_layer = None

                for idx, row in county_outline.iterrows():
                    properties = {}
                    # Add county name if available
                    if 'name' in county_outline.columns:
                        properties['name'] = row['name']

                    layer_data = LayerData(
                        layer_id=county_layer.id,
                        geometry=from_shape(row.geometry, srid=4326),
                        properties=json.dumps(properties),
                        feature_id=f"county_outline_{idx}"
                    )
                    session.add(layer_data)

                    # Also add county labels as a separate layer
                    if 'name' in county_outline.columns:
                        # Get centroid for label placement
                        centroid = row.geometry.centroid

                        # Create or get county labels layer if it doesn't exist
                        if county_labels_layer is None:
                            county_labels_layer = session.query(Layers).filter_by(
                                layer_group_id=admin_group.id,
                                layer_name="County Labels"
                            ).first()

                            if not county_labels_layer:
                                county_labels_layer = Layers(
                                    layer_group_id=admin_group.id,
                                    layer_name="County Labels",
                                    layer_type="point",
                                    display_order=2,
                                    is_visible_by_default=True,
                                    style_config=json.dumps({
                                        "radius": 0,  # Make the point invisible
                                        "showLabel": True,
                                        "labelOptions": {
                                            "noHide": True,
                                            "direction": "center",
                                            "permanent": True
                                        }
                                    })
                                )
                                session.add(county_labels_layer)
                                session.commit()

                        # Add label point
                        label_data = LayerData(
                            layer_id=county_labels_layer.id,
                            geometry=from_shape(centroid, srid=4326),
                            properties=json.dumps({"name": row['name']}),
                            feature_id=f"county_label_{idx}"
                        )
                        session.add(label_data)

                session.commit()
                print(f"Added county outlines and labels to database")

        # Process BEAD Eligible Locations
        if os.path.exists(bead_eligible_locations_file):
            print(f"Processing BEAD eligible locations from {bead_eligible_locations_file}")
            bead_eligible_locations = gpd.read_file(bead_eligible_locations_file).set_crs("EPSG:4326")

            # Create or get layer
            bead_layer = session.query(Layers).filter_by(layer_group_id=bead_group.id,
                                                         layer_name="BEAD Eligible Locations").first()
            if not bead_layer:
                bead_layer = Layers(
                    layer_group_id=bead_group.id,
                    layer_name="BEAD Eligible Locations",
                    layer_type="point",
                    display_order=0,
                    is_visible_by_default=True,
                    style_config=json.dumps({
                        "radius": 4,
                        "color": "black",
                        "fillColor": "#01fbff",
                        "weight": 1,
                        "opacity": 1,
                        "fillOpacity": 1
                    })
                )
                session.add(bead_layer)
                session.commit()

            # Add BEAD eligible location points if they don't exist yet
            if session.query(func.count(LayerData.id)).filter_by(layer_id=bead_layer.id).scalar() == 0:
                # Process in batches to avoid memory issues
                batch_size = 1000
                for start_idx in range(0, len(bead_eligible_locations), batch_size):
                    end_idx = min(start_idx + batch_size, len(bead_eligible_locations))
                    batch = bead_eligible_locations.iloc[start_idx:end_idx]

                    for idx, row in batch.iterrows():
                        properties = {}
                        # Add any additional properties from the GeoDataFrame
                        for col in bead_eligible_locations.columns:
                            if col != 'geometry' and not pd.isna(row[col]):
                                try:
                                    # Convert numpy data types to Python native types
                                    value = row[col]
                                    if hasattr(value, 'item'):
                                        properties[col] = value.item()
                                    else:
                                        properties[col] = value
                                except:
                                    # Skip if conversion fails
                                    pass

                        try:
                            layer_data = LayerData(
                                layer_id=bead_layer.id,
                                geometry=from_shape(row.geometry, srid=4326),
                                properties=json.dumps(properties),
                                feature_id=f"bead_location_{idx}"
                            )
                            session.add(layer_data)
                        except Exception as e:
                            print(f"Error adding BEAD location {idx}: {str(e)}")
                            continue

                    session.commit()
                    print(f"Added BEAD eligible locations batch {start_idx}-{end_idx} to database")

                print(f"Added all BEAD eligible locations to database")

        # Process Grid Analysis Layer
        if os.path.exists(e):
            print(f"Processing grid analysis layer from {grid_analysis_layer_file}")
            grid_analysis_layer = gpd.read_file(grid_analysis_layer_file)[['geometry', 'point_count']].set_crs(
                "EPSG:4326")

            # Define ranges and colors
            range_dict = {
                "0": {"range": (1, 5), "color": "#e4e4f3"},
                "1": {"range": (5, 10), "color": "#d1d1ea"},
                "2": {"range": (10, 20), "color": "#b3b3e0"},
                "3": {"range": (20, 30), "color": "#8080c5"},
                "4": {"range": (30, 50), "color": "#6d6dbd"},
                "5": {"range": (50, 75), "color": "#4949ac"},
                "6": {"range": (75, 100), "color": "#3737a4"},
                "7": {"range": (100, 50000), "color": "#121293"},
            }

            # Create or get grid layers for each range
            for key, value in range_dict.items():
                range_min, range_max = value["range"]
                color = value["color"]

                layer_naming = f"Grid Layer ({range_min}-{range_max} Locations)"
                if range_min == 100:
                    layer_naming = f"Grid Layer ({range_min}+ Locations)"

                # Create or get layer
                grid_layer = session.query(Layers).filter_by(layer_group_id=bead_group.id,
                                                             layer_name=layer_naming).first()
                if not grid_layer:
                    grid_layer = Layers(
                        layer_group_id=bead_group.id,
                        layer_name=layer_naming,
                        layer_type="polygon",
                        display_order=int(key) + 1,  # Use the key as order
                        is_visible_by_default=False,
                        style_config=json.dumps({
                            "fillColor": color,
                            "color": color,
                            "weight": 1,
                            "fillOpacity": 0.6
                        })
                    )
                    session.add(grid_layer)
                    session.commit()

                # Filter grid cells for this range
                range_layer = grid_analysis_layer[
                    (grid_analysis_layer["point_count"] >= range_min) &
                    (grid_analysis_layer["point_count"] < range_max)
                    ]

                # Add grid cells if they don't exist yet
                if not range_layer.empty and session.query(func.count(LayerData.id)).filter_by(
                        layer_id=grid_layer.id).scalar() == 0:
                    try:
                        # Dissolve geometries for efficiency
                        dissolved_geometry = unary_union(range_layer['geometry'])

                        # Create GeoDataFrame with dissolved geometry
                        dissolved_gdf = gpd.GeoDataFrame(geometry=[dissolved_geometry], crs="EPSG:4326")

                        for idx, row in dissolved_gdf.iterrows():
                            properties = {
                                "range_min": range_min,
                                "range_max": range_max
                            }

                            layer_data = LayerData(
                                layer_id=grid_layer.id,
                                geometry=from_shape(row.geometry, srid=4326),
                                properties=json.dumps(properties),
                                feature_id=f"grid_range_{key}_{idx}"
                            )
                            session.add(layer_data)

                        session.commit()
                        print(f"Added grid layer for range {range_min}-{range_max} to database")
                    except Exception as e:
                        print(f"Error processing grid layer {layer_naming}: {str(e)}")
                        session.rollback()

        # Process WISP layers
        if os.path.isdir(wisp_folder):
            print(f"Processing WISP layers from {wisp_folder}")

            for file in os.listdir(wisp_folder):
                if file.endswith(".sqlite"):
                    file_path = os.path.join(wisp_folder, file)
                    wisp_name = os.path.splitext(file)[0]
                    color = get_wisp_color(wisp_name)

                    print(f"Processing WISP: {wisp_name} with color {color}")

                    # Create or get layer
                    wisp_layer = session.query(Layers).filter_by(
                        layer_group_id=wisp_group.id,
                        layer_name=f"WISP - {wisp_name}"
                    ).first()

                    if not wisp_layer:
                        wisp_layer = Layers(
                            layer_group_id=wisp_group.id,
                            layer_name=f"WISP - {wisp_name}",
                            layer_type="polygon",
                            display_order=0,  # All WISPs at same level
                            is_visible_by_default=False,
                            style_config=json.dumps({
                                "fillColor": color,
                                "color": color,
                                "weight": 1,
                                "fillOpacity": 0.6
                            })
                        )
                        session.add(wisp_layer)
                        session.commit()

                    # Add WISP geometry if it doesn't exist yet
                    if session.query(func.count(LayerData.id)).filter_by(layer_id=wisp_layer.id).scalar() == 0:
                        try:
                            wisp_gdf = gpd.read_file(file_path)[['geometry']].set_crs("EPSG:4326")

                            for idx, row in wisp_gdf.iterrows():
                                properties = {
                                    "wisp_name": wisp_name
                                }

                                layer_data = LayerData(
                                    layer_id=wisp_layer.id,
                                    geometry=from_shape(row.geometry, srid=4326),
                                    properties=json.dumps(properties),
                                    feature_id=f"wisp_{wisp_name}_{idx}"
                                )
                                session.add(layer_data)

                            session.commit()
                            print(f"Added WISP layer for {wisp_name} to database")
                        except Exception as e:
                            print(f"Error processing WISP layer {wisp_name}: {str(e)}")
                            session.rollback()

        print(f"Successfully created map data for {state_name} in the database")
        return project.id

    except Exception as e:
        session.rollback()
        print(f"Error creating map data: {str(e)}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Create map data in the database')
    parser.add_argument('--base-folder', required=True, help='Base folder containing map data')
    parser.add_argument('--state-name', required=True, help='Name of the state')
    parser.add_argument('--wisp-folder', default='', help='Folder containing WISP data (optional)')
    parser.add_argument('--state-outline', default='', help='State outline file (optional)')
    parser.add_argument('--county-outline', default='', help='County outline file (optional)')
    parser.add_argument('--bead-locations', default='', help='BEAD eligible locations file (optional)')
    parser.add_argument('--grid-analysis', default='', help='Grid analysis layer file (optional)')
    parser.add_argument('--db-url', default=None, help='Database connection URL (optional)')

    args = parser.parse_args()

    create_map_in_database(
        base_folder=args.base_folder,
        state_name=args.state_name,
        wisp_folder=args.wisp_folder,
        state_outline_file=args.state_outline,
        county_outline_file=args.county_outline,
        bead_eligible_locations_file=args.bead_locations,
        grid_analysis_layer_file=args.grid_analysis,
        db_url=args.db_url
    )


if __name__ == "__main__":
    main()