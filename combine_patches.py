import arcpy
from arcpy.sa import *
import os
import sys

# ArcGIS Extensions
if arcpy.CheckExtension("Spatial") == "Available":
    arcpy.AddMessage("Checking out Spatial")
    arcpy.CheckOutExtension("Spatial")
else:
    arcpy.AddError("Unable to get spatial analyst extension")
    arcpy.AddMessage(arcpy.GetMessages(0))
    sys.exit(0)


# inputs
dem = arcpy.GetParameterAsText(0)
patch_dir = arcpy.GetParameterAsText(1)
arcpy.env.workspace = patch_dir
outdem_path = '%s_patched%s' % os.path.splitext(dem)

rasters = arcpy.ListRasters()
arcpy.AddMessage(patch_dir)
arcpy.AddMessage(rasters)
outdem = Raster(dem)
arcpy.env.extent = outdem.extent
arcpy.env.snapRaster = outdem
for raster in rasters:
    print ("Patching with: %s" % os.path.join(patch_dir, raster))
    outdem = Con(IsNull(raster), outdem, raster)

outdem.save(outdem_path)
