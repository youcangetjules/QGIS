from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeatureRequest, QgsFeature, QgsGeometry,
    QgsField, QgsProcessingFeedback, QgsExpression
)
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import QVariant
import processing

# --- Helper: Select a loaded layer from the project ---
def select_layer_interactively(prompt):
    layers = QgsProject.instance().mapLayers().values()
    layer_names = [layer.name() for layer in layers]
    selected, ok = QInputDialog.getItem(None, "Select Layer", prompt, layer_names, editable=False)
    if ok and selected:
        return QgsProject.instance().mapLayersByName(selected)[0]
    else:
        raise Exception("Layer selection was cancelled or invalid.")

# --- Parameters ---
buffer_distance = 50  # in meters
dBm_field = "dbm"  # Field name for signal strength

# --- Interactive layer selection ---
mobile_layer_1 = select_layer_interactively("Select the first mobile coverage layer.")
mobile_layer_2 = select_layer_interactively("Select the second mobile coverage layer.")
output_layer = select_layer_interactively("Select the output area layer.")
landuse_layer = select_layer_interactively("Select the OSM land use layer.")

# --- Reproject a layer to EPSG:3857 ---
def reproject_layer(layer):
    result = processing.run("native:reprojectlayer", {
        "INPUT": layer,
        "TARGET_CRS": "EPSG:3857",
        "OUTPUT": "memory:"
    })["OUTPUT"]
    return result

mobile_layer_1_reprojected = reproject_layer(mobile_layer_1)
mobile_layer_2_reprojected = reproject_layer(mobile_layer_2)

# --- Filter features by dBm threshold ---
def filter_by_dBm(layer, threshold, op="lte"):
    expr = f'"{dBm_field}" {"<=" if op == "lte" else ">"} {threshold}'
    request = QgsFeatureRequest(QgsExpression(expr))
    return [f for f in layer.getFeatures(request)]

# Thresholds
threshold_blackspot = -119
threshold_strong_signal = -100

# Blackspots and strong signals
blackspot_feats_1 = filter_by_dBm(mobile_layer_1_reprojected, threshold_blackspot, "lte")
strong_feats_1 = filter_by_dBm(mobile_layer_1_reprojected, threshold_strong_signal, "gt")
blackspot_feats_2 = filter_by_dBm(mobile_layer_2_reprojected, threshold_blackspot, "lte")
strong_feats_2 = filter_by_dBm(mobile_layer_2_reprojected, threshold_strong_signal, "gt")

# --- Buffer creation ---
def create_buffer_layer(features, name):
    buf_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", name, "memory")
    provider = buf_layer.dataProvider()
    provider.addAttributes([QgsField("grp", QVariant.Int)])
    buf_layer.updateFields()

    for f in features:
        geom = f.geometry()
        if geom:
            buffer = geom.buffer(buffer_distance, 8)
            feat = QgsFeature(buf_layer.fields())
            feat.setGeometry(buffer)
            feat.setAttribute("grp", 1)
            provider.addFeature(feat)

    buf_layer.updateExtents()
    QgsProject.instance().addMapLayer(buf_layer)
    return buf_layer

buffer_blackspot_1 = create_buffer_layer(blackspot_feats_1, "Buffer_Blackspot_1")
buffer_blackspot_2 = create_buffer_layer(blackspot_feats_2, "Buffer_Blackspot_2")
buffer_strong_1 = create_buffer_layer(strong_feats_1, "Buffer_Strong_1")
buffer_strong_2 = create_buffer_layer(strong_feats_2, "Buffer_Strong_2")

# --- Dissolve buffers ---
def dissolve_layer(layer):
    result = processing.run("native:dissolve", {
        "INPUT": layer,
        "FIELD": ["grp"],
        "OUTPUT": "memory:"
    })["OUTPUT"]
    return result

dissolved_blackspot_1 = dissolve_layer(buffer_blackspot_1)
dissolved_blackspot_2 = dissolve_layer(buffer_blackspot_2)
dissolved_strong_1 = dissolve_layer(buffer_strong_1)
dissolved_strong_2 = dissolve_layer(buffer_strong_2)

# --- Union strong signals into one layer ---
def union_layers(layer1, layer2):
    result = processing.run("native:union", {
        "INPUT": layer1,
        "INPUT_2": layer2,
        "OUTPUT": "memory:"
    })["OUTPUT"]
    return result

dissolved_strong = union_layers(dissolved_strong_1, dissolved_strong_2)

# --- Subtract strong signal from blackspots ---
def subtract_layer(base, subtractor):
    result = processing.run("native:difference", {
        "INPUT": base,
        "OVERLAY": subtractor,
        "OUTPUT": "memory:"
    })["OUTPUT"]
    return result

final_blackspot_1 = subtract_layer(dissolved_blackspot_1, dissolved_strong)
final_blackspot_2 = subtract_layer(dissolved_blackspot_2, dissolved_strong)

# --- Combine final blackspots ---
combined_blackspots = union_layers(final_blackspot_1, final_blackspot_2)

# --- Remove landuse areas (e.g., farmland) ---
def remove_landuse_types(input_layer, landuse_layer, excluded_types):
    filtered_geoms = [f.geometry() for f in landuse_layer.getFeatures() if f["landuse"] in excluded_types]
    result_layer = input_layer
    for geom in filtered_geoms:
        result_layer = processing.run("native:difference", {
            "INPUT": result_layer,
            "OVERLAY": QgsVectorLayer(geom.asWkt(), "temp", "memory"),
            "OUTPUT": "memory:"
        })["OUTPUT"]
    return result_layer

excluded_types = ["farmland", "grass", "meadow", "scrub"]  # Modify as needed
final_blackspots = remove_landuse_types(combined_blackspots, landuse_layer, excluded_types)

# --- Add final output layer to QGIS ---
final_blackspots.setName("Final_Blackspot_Polygons")
QgsProject.instance().addMapLayer(final_blackspots)