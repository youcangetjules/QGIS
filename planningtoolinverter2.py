from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField,
    QgsPointXY, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProcessingFeedback
)
from PyQt5.QtCore import QVariant
import math
import processing

# --- Helper: Select a layer by name ---
def select_layer(prompt):
    layers = QgsProject.instance().mapLayers().values()
    layer_names = [layer.name() for layer in layers]
    from PyQt5.QtWidgets import QInputDialog
    selected, ok = QInputDialog.getItem(None, "Select Layer", prompt, layer_names, editable=False)
    if ok and selected:
        return QgsProject.instance().mapLayersByName(selected)[0]
    else:
        raise Exception("Layer selection was cancelled or invalid.")

# --- Parameters ---
beam_width = 65  # degrees
radius = 2500  # in meters
azimuth_field = "Azimuth"
lat_field = "Lat"
lon_field = "Long"

# --- Select input layers ---
tower_layer = select_layer("Select tower layer with Lat, Long, and Azimuth")
coverage_layer = select_layer("Select coverage shapefile layer")
osm_landuse_layer = select_layer("Select the OSM landuse layer")

# --- Reproject layer to EPSG:3857 ---
def reproject_to_3857(layer):
    return processing.run("native:reprojectlayer", {
        'INPUT': layer,
        'TARGET_CRS': 'EPSG:3857',
        'OUTPUT': 'memory:'
    })['OUTPUT']

# --- Generate coverage wedges ---
def generate_wedges(layer, azimuth_field, lat_field, lon_field, beam_width, radius):
    crsSrc = QgsCoordinateReferenceSystem("EPSG:4326")
    crsDest = QgsCoordinateReferenceSystem("EPSG:3857")
    xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())

    wedge_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", "Wedges", "memory")
    provider = wedge_layer.dataProvider()
    provider.addAttributes([QgsField("Azimuth", QVariant.Double)])
    wedge_layer.updateFields()

    for feat in layer.getFeatures():
        azimuth = float(feat[azimuth_field])
        lat = float(feat[lat_field])
        lon = float(feat[lon_field])

        center = QgsPointXY(lon, lat)
        center_proj = xform.transform(center)

        start_angle = azimuth - beam_width / 2
        end_angle = azimuth + beam_width / 2

        segments = []
        segments.append(center_proj)

        for angle in range(int(start_angle), int(end_angle) + 1, 1):
            angle_rad = math.radians(angle)
            x = center_proj.x() + radius * math.sin(angle_rad)
            y = center_proj.y() + radius * math.cos(angle_rad)
            segments.append(QgsPointXY(x, y))

        segments.append(center_proj)  # close wedge

        geometry = QgsGeometry.fromPolygonXY([segments])
        new_feat = QgsFeature(wedge_layer.fields())
        new_feat.setGeometry(geometry)
        new_feat.setAttributes([azimuth])
        provider.addFeature(new_feat)

    wedge_layer.updateExtents()
    QgsProject.instance().addMapLayer(wedge_layer)
    return wedge_layer

# --- Main logic ---
reprojected_coverage = reproject_to_3857(coverage_layer)
reprojected_osm = reproject_to_3857(osm_landuse_layer)
wedge_layer = generate_wedges(tower_layer, azimuth_field, lat_field, lon_field, beam_width, radius)

# --- Invert coverage area from wedge ---
def subtract_coverage_from_wedges(wedge_layer, coverage_layer):
    result = processing.run("native:difference", {
        "INPUT": wedge_layer,
        "OVERLAY": coverage_layer,
        "OUTPUT": "memory:"
    })["OUTPUT"]
    return result

no_coverage_area = subtract_coverage_from_wedges(wedge_layer, reprojected_coverage)

# --- Filter landuse polygons to residential/commercial/etc ---
residential_types = ['residential', 'commercial', 'industrial', 'retail']
expression = ' OR '.join([f'"landuse" = \'{t}\'' for t in residential_types])
residential_areas = processing.run("native:extractbyexpression", {
    "INPUT": reprojected_osm,
    "EXPRESSION": expression,
    "OUTPUT": "memory:"
})["OUTPUT"]

# --- Clip no coverage wedges to populated areas only ---
final_no_coverage = processing.run("native:intersection", {
    "INPUT": no_coverage_area,
    "OVERLAY": residential_areas,
    "OUTPUT": "memory:"
})["OUTPUT"]

# --- Add to QGIS ---
final_no_coverage.setName("No_Coverage_Populated_Areas_Only")
QgsProject.instance().addMapLayer(final_no_coverage)

