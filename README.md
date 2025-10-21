# 📡 QGIS Mobile Signal Blackspot Analyzer

Automated QGIS script for identifying mobile coverage blackspots using signal strength layers and OSM land use data.

This Python script runs inside QGIS’s Python console (or as a Processing script) to detect, map, and clean mobile network blackspot zones based on signal strength thresholds from two coverage datasets. It automatically buffers, filters, and subtracts areas of strong coverage, then removes irrelevant land use areas (like farmland) to focus on meaningful public zones.

## 🚀 Features

Interactive layer selection – Select layers from your active QGIS project via dialog boxes.

Automatic reprojection – Reprojects layers to EPSG:3857 for consistent analysis.

Signal-based filtering – Identifies weak and strong signal regions using configurable dBm thresholds.

Buffered coverage zones – Expands poor-signal regions spatially for more realistic analysis.

Union and difference operations – Removes strong-signal overlaps and merges multi-network results.

Land use exclusion – Optionally removes farmland, grassland, scrub, and other irrelevant areas using OSM data.

In-memory processing – All layers are created dynamically in memory, keeping your project clean.

## ⚙️ Workflow Overview

Select Input Layers

Two mobile signal coverage layers (each containing a dbm field).

An output area layer (for spatial reference).

An OSM landuse layer for filtering.

Automatic Processing Steps

Reproject → Filter (by dBm) → Buffer → Dissolve → Union/Difference → Landuse exclusion.

Result

A new layer called Final_Blackspot_Polygons added to your QGIS project.

## 🧩 Configuration

Edit these parameters at the top of the script as needed:

buffer_distance = 50       # Buffer radius in meters
dBm_field = "dbm"          # Field name for signal strength
threshold_blackspot = -119 # dBm threshold for poor coverage
threshold_strong_signal = -100 # dBm threshold for strong coverage
excluded_types = ["farmland", "grass", "meadow", "scrub"] # Landuse types to exclude

## 🖥️ Usage

Open QGIS.

Load your coverage and land use layers.

Open the Python Console (Plugins → Python Console).

Paste and run the script.

Select layers as prompted.

The final blackspot polygons will appear in your QGIS project.

## 🧠 Requirements

QGIS 3.22+ (tested on QGIS 3.36+)

PyQt5, QGIS Processing Framework (built-in)

Coverage layers must include a numeric dbm field.

## 📄 License

This project is released under the MIT License
.

## 💡 Example Use Case

This tool can be used by:

Telecom analysts assessing network overlap or weak coverage areas.

Local councils mapping underserved regions.

Researchers correlating land use with signal quality.
