import arcpy
import os
import shutil
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
patch = arcpy.GetParameterAsText(0)  # C:\Users\kfisher\Downloads\f_dem\patch.shp
height_adjustment = arcpy.GetParameterAsText(1)  # C:\Users\kfisher\Downloads\f_dem\height_adj.shp
height_field = arcpy.GetParameterAsText(2)  # height
demfile = arcpy.GetParameterAsText(3)  # C:\Users\kfisher\Downloads\f_dem\f_dem.tif
outfile = arcpy.GetParameterAsText(4)  # C:\Users\kfisher\Downloads\f_dem\output\outdem.tif

arcpy.env.overwriteOutput = True
TEMP_DIR = os.path.join(os.path.dirname(outfile), 'temp')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# clear existing temp files
for the_file in os.listdir(TEMP_DIR):
    file_path = os.path.join(TEMP_DIR, the_file)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print(e)


def patch_dem(patch_polygons, height_adj, dem, out_raster):
    # get cell size
    dem_result = arcpy.GetRasterProperties_management(dem, "CELLSIZEX")
    cell_size = dem_result.getOutput(0)

    # convert polygon to line
    temp_line = os.path.join(TEMP_DIR, 'temp_line.shp')
    arcpy.PolygonToLine_management(patch_polygons,
                                   temp_line,
                                   "IGNORE_NEIGHBORS")

    # convert line to raster perimeter
    value_field = "Id"
    temp_raster = os.path.join(TEMP_DIR, "temp_raster.tif")
    arcpy.PolylineToRaster_conversion(in_features=temp_line,
                                      value_field=value_field,
                                      out_rasterdataset=temp_raster,
                                      cellsize=cell_size)

    # extract dem values to perimeter
    dem_perimeter = arcpy.sa.Con(temp_raster, dem, temp_raster)
    temp_point = os.path.join(TEMP_DIR, "temp_point.shp")

    # convert perimeter cells to points for topo to raster
    arcpy.RasterToPoint_conversion(dem_perimeter, temp_point, "VALUE")

    # convert patch polygon to raster
    patch_raster = os.path.join(TEMP_DIR, "patch.tif")
    arcpy.PolygonToRaster_conversion(in_features=patch_polygons,
                                     value_field="FID",
                                     out_rasterdataset=patch_raster,
                                     cellsize=cell_size)

    # merge the cells from rasterized perimeter with rasterized polygon for use as mask
    patch_merge = os.path.join(TEMP_DIR, "patch_merge.tif")
    patch_merge_raster = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(patch_raster)) == 0,
                                      arcpy.Raster(patch_raster),
                                      dem_perimeter)
    patch_merge_raster.save(patch_merge)

    temp_point_dem = os.path.join(TEMP_DIR, "temp_point_dem.shp")
    arcpy.sa.ExtractValuesToPoints(temp_point, dem, temp_point_dem)

    height_adj_points = [height_adj, height_field]
    # If height_adj is a contour line, convert to points
    shape_type = arcpy.Describe(height_adj).shapeType
    arcpy.AddMessage(shape_type)
    if shape_type == 'Polyline':
        # convert contour line to raster perimeter
        temp_raster_contour = os.path.join(TEMP_DIR, "temp_raster_contour.tif")
        arcpy.PolylineToRaster_conversion(in_features=height_adj,
                                          value_field=height_field,
                                          out_rasterdataset=temp_raster_contour,
                                          cellsize=cell_size)
        contour_points = os.path.join(TEMP_DIR, "temp_contour_points.shp")
        arcpy.RasterToPoint_conversion(temp_raster_contour, contour_points, "VALUE")
        height_adj_points = [contour_points, "grid_code"]

    # run topo_to_raster using perimeter values from existing dem and height adjustment points
    point_elevation = arcpy.sa.TopoPointElevation([height_adj_points, [temp_point_dem, "RASTERVALU"]])
    out_ttr = arcpy.sa.TopoToRaster(point_elevation, cell_size=cell_size, data_type='SPOT')

    # apply mask
    arcpy.env.mask = patch_merge
    out_ttr += 0
    out_ttr.save(out_raster)
    arcpy.env.mask = None


arcpy.env.snapRaster = demfile

patch_dem(patch_polygons=patch,
          height_adj=height_adjustment,
          dem=demfile,
          out_raster=outfile)
