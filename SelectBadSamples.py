from qgis.core import (
    QgsProject,
    QgsExpression,
    QgsVectorLayer,
    QgsFeatureRequest,
    QgsGeometry,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsVectorLayerUtils,
    QgsProcessingFeedback
)
from PyQt5.QtCore import QVariant
import processing

# --- Parameters ---
layer_name = "three mnsi raw - w column headers"
dBm_field = "dbm"
threshold = -115
buffer_distance = 50  # meters

# --- Get and reproject input layer ---
input_layer = QgsProject.instance().mapLayersByName(layer_name)[0]

reprojected = processing.run("native:reprojectlayer", {
    "INPUT": input_layer,
    "TARGET_CRS": "EPSG:3857",
    "OUTPUT": "memory:"
})["OUTPUT"]

# --- Filter features ≤ -115 dBm ---
expr = f"\"{dBm_field}\" <= {threshold}"
request = QgsFeatureRequest(QgsExpression(expr))
selected_features = [f for f in reprojected.getFeatures(request)]

# --- Buffer features into memory layer ---
buffer_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", "Buffered_Blackspots", "memory")
prov = buffer_layer.dataProvider()
prov.addAttributes([QgsField("grp", QVariant.Int)])
buffer_layer.updateFields()

for feat in selected_features:
    geom = feat.geometry()
    if geom:
        buffered = geom.buffer(buffer_distance, 8)
        f = QgsFeature(buffer_layer.fields())
        f.setGeometry(buffered)
        f["grp"] = 1  # dummy value to allow dissolve
        prov.addFeature(f)

buffer_layer.updateExtents()
QgsProject.instance().addMapLayer(buffer_layer)

# --- Dissolve based on dummy field to merge overlaps ---
feedback = QgsProcessingFeedback()
dissolved = processing.run("native:dissolve", {
    "INPUT": buffer_layer,
    "FIELD": ["grp"],  # Dissolve by dummy field
    "OUTPUT": "memory:"
}, feedback=feedback)["OUTPUT"]

# --- Break multiparts into single polygons ---
singleparts = processing.run("native:multiparttosingleparts", {
    "INPUT": dissolved,
    "OUTPUT": "memory:"
})["OUTPUT"]

singleparts.setName("Blackspot_Polygons")
QgsProject.instance().addMapLayer(singleparts)
