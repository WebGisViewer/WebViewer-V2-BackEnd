# layers/utils.py
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.contrib.gis.gdal import SpatialReference, CoordTransform
import json
import zipfile
import tempfile
import os
import shutil


def convert_to_geojson(geometry, properties=None):
    """Convert a GEOS geometry to GeoJSON Feature."""
    if properties is None:
        properties = {}

    feature = {
        'type': 'Feature',
        'geometry': json.loads(geometry.json),
        'properties': properties
    }
    return feature


def create_feature_collection(features):
    """Create a GeoJSON FeatureCollection from a list of features."""
    feature_collection = {
        'type': 'FeatureCollection',
        'features': features
    }
    return feature_collection


def reproject_geometry(geometry, from_srid, to_srid=4326):
    """Reproject a geometry from one coordinate system to another."""
    source_srs = SpatialReference(from_srid)
    target_srs = SpatialReference(to_srid)

    transform = CoordTransform(source_srs, target_srs)
    geometry.transform(transform)

    return geometry


def simplify_geometry(geometry, tolerance=0.0001):
    """Simplify a geometry to reduce complexity while preserving shape."""
    return geometry.simplify(tolerance=tolerance, preserve_topology=True)


def extract_shapefile(shapefile_zip):
    """Extract a zipped shapefile to a temporary directory."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Extract all files to the temporary directory
        with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Check for required files
        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        if not shp_files:
            raise ValueError("No .shp file found in the zipfile")

        # Return the path to the .shp file
        return os.path.join(temp_dir, shp_files[0]), temp_dir

    except Exception as e:
        # Clean up in case of error
        shutil.rmtree(temp_dir)
        raise e


def cleanup_temp_dir(temp_dir):
    """Clean up temporary directory."""
    shutil.rmtree(temp_dir)