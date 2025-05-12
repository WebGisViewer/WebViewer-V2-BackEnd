# layers/file_utils.py

import os
import uuid
import tempfile
import shutil
from pathlib import Path
import geopandas as gpd
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import zipfile
from django.utils import timezone

from layers.models import ProjectLayerData


def get_crs_from_file(file_path, file_type):
    """
    Extract CRS from a geospatial file.
    Returns tuple: (crs_found, crs_auth_code, crs_name)
    """
    try:
        # Handle different file types
        if file_type == 'shp':
            # Need to extract all components from zip
            if file_path.endswith('.zip'):
                temp_dir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    # Find .shp file in the extracted directory
                    shp_files = list(Path(temp_dir).glob('**/*.shp'))

                    if not shp_files:
                        return False, None, "No .shp file found in zip archive"

                    gdf = gpd.read_file(shp_files[0])
                except Exception as e:
                    shutil.rmtree(temp_dir)
                    return False, None, f"Error reading shapefile: {str(e)}"
                finally:
                    shutil.rmtree(temp_dir)
            else:
                # Direct shapefile
                gdf = gpd.read_file(file_path)

        elif file_type == 'kml':
            gdf = gpd.read_file(file_path, driver='KML')

        elif file_type == 'sqlite':
            gdf = gpd.read_file(file_path, driver='SQLite')

        else:
            return False, None, f"Unsupported file type: {file_type}"

        # Check if CRS exists
        if gdf.crs is None:
            return False, None, "No CRS defined in file"

        # Get CRS auth code (like EPSG:4326)
        try:
            auth_code = f"{gdf.crs.to_authority()[0]}:{gdf.crs.to_authority()[1]}"
            return True, auth_code, gdf.crs.name
        except (AttributeError, ValueError, TypeError) as e:
            # Try to get some representation even if not standard
            crs_str = str(gdf.crs)
            return True, None, crs_str

    except Exception as e:
        return False, None, str(e)


def get_supported_crs_list():
    """
    Return a list of common CRS options for user selection.
    """
    common_crs = [
        {"code": "EPSG:4326", "name": "WGS 84", "description": "World Geodetic System 1984, used in GPS"},
        {"code": "EPSG:3857", "name": "Web Mercator", "description": "Used by many web mapping applications"},
        {"code": "EPSG:26916", "name": "NAD83 UTM 16N", "description": "UTM Zone 16N using NAD83"},
        {"code": "EPSG:26917", "name": "NAD83 UTM 17N", "description": "UTM Zone 17N using NAD83"},
        {"code": "EPSG:26918", "name": "NAD83 UTM 18N", "description": "UTM Zone 18N using NAD83"},
        {"code": "EPSG:26919", "name": "NAD83 UTM 19N", "description": "UTM Zone 19N using NAD83"},
        {"code": "EPSG:32616", "name": "WGS 84 UTM 16N", "description": "UTM Zone 16N using WGS84"},
        {"code": "EPSG:32617", "name": "WGS 84 UTM 17N", "description": "UTM Zone 17N using WGS84"},
        {"code": "EPSG:32618", "name": "WGS 84 UTM 18N", "description": "UTM Zone 18N using WGS84"},
        {"code": "EPSG:32619", "name": "WGS 84 UTM 19N", "description": "UTM Zone 19N using WGS84"},
        {"code": "EPSG:3734", "name": "NAD83 Ohio South", "description": "NAD83 Ohio South (HARN / NSRS2007)"},
        {"code": "EPSG:3735", "name": "NAD83 Ohio North", "description": "NAD83 Ohio North (HARN / NSRS2007)"},
        {"code": "EPSG:2272", "name": "NAD83 Pennsylvania South", "description": "NAD83 Pennsylvania South"},
        {"code": "EPSG:2271", "name": "NAD83 Pennsylvania North", "description": "NAD83 Pennsylvania North"},
    ]
    return common_crs


def store_uploaded_file(upload_file, file_type):
    """
    Store an uploaded file in a temporary location.
    Returns: (file_path, file_id)
    """
    # Generate a unique ID for this file
    file_id = str(uuid.uuid4())

    # Determine storage directory
    upload_dir = getattr(settings, 'TEMP_UPLOAD_DIR', 'temp_uploads')

    # Create full path with unique ID
    file_name = f"{file_id}.{file_type}"
    file_path = os.path.join(upload_dir, file_name)

    # Store file
    path = default_storage.save(file_path, ContentFile(upload_file.read()))

    # Return full path and ID
    return default_storage.path(path), file_id


def detect_file_type(file_obj):
    """
    Detect the geospatial file type from the file extension.
    """
    filename = file_obj.name.lower()

    if filename.endswith('.shp') or filename.endswith('.zip'):
        return 'shp'
    elif filename.endswith('.kml'):
        return 'kml'
    elif filename.endswith('.sqlite'):
        return 'sqlite'
    else:
        return None


def import_file_to_layer(layer, file_path, file_type, source_crs=None, target_crs='EPSG:4326'):
    """
    Import geospatial file contents to a layer.
    """
    try:
        # Read the file with geopandas
        if file_type == 'shp':
            # Check if it's a zip file containing shapefile
            if file_path.endswith('.zip'):
                temp_dir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    # Find .shp file in the extracted directory
                    shp_files = list(Path(temp_dir).glob('**/*.shp'))

                    if not shp_files:
                        raise ValueError("No .shp file found in zip archive")

                    gdf = gpd.read_file(shp_files[0])
                finally:
                    shutil.rmtree(temp_dir)
            else:
                # Direct shapefile
                gdf = gpd.read_file(file_path)

        elif file_type == 'kml':
            gdf = gpd.read_file(file_path, driver='KML')

        elif file_type == 'sqlite':
            gdf = gpd.read_file(file_path)
            print(gdf.head())
            print(gdf.columns)
            import fiona
            print(fiona.listlayers(file_path))

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Set CRS if specified and not defined in file
        if source_crs and gdf.crs is None:
            gdf.crs = source_crs

        # If CRS is still None, raise an error
        if gdf.crs is None:
            raise ValueError("No CRS defined in file and none provided")

        # Reproject to target CRS if needed
        if gdf.crs != target_crs:
            gdf = gdf.to_crs(target_crs)

        # Import features to layer
        features = []
        for _, row in gdf.iterrows():
            try:
                wkt = row.geometry.wkt
                geom = GEOSGeometry(wkt)

                properties = {}
                for col in gdf.columns:
                    if col != 'geometry':
                        value = row[col]
                        if hasattr(value, 'item'):
                            value = value.item()
                        properties[col] = value

                # Create feature object but don't save yet
                feature = ProjectLayerData(
                    project_layer=layer,
                    geometry=geom,
                    properties=properties
                )
                features.append(feature)

            except Exception as e:
                print(f"Error processing row: {e}")
                continue

        # Bulk insert in batches (PostgreSQL has a limit on parameters)
        batch_size = 1000
        for i in range(0, len(features), batch_size):
            batch = features[i:i + batch_size]
            ProjectLayerData.objects.bulk_create(batch)

        features_count = len(features)
        # Update layer with import stats
        layer.feature_count = features_count
        layer.last_data_update = timezone.now()
        layer.upload_status = 'complete'
        layer.save()

        return True, features_count, None

    except Exception as e:
        # Update layer with error
        layer.upload_status = 'failed'
        layer.upload_error = str(e)
        layer.save()

        return False, 0, str(e)