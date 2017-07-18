import arcpy
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
patch = arcpy.GetParameterAsText(0)
height_adjustment = arcpy.GetParameterAsText(1)
dem = arcpy.GetParameterAsText(2)
out_path = arcpy.GetParameterAsText(3)

# directories
PROJECT_DIR = r'F:\working_copies\dem_patch'
TEMP_DIR = os.path.join(PROJECT_DIR, 'temp')


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
    patch_merge_raster = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(patch_raster)) == 0, arcpy.Raster(patch_raster), dem_perimeter)
    patch_merge_raster.save(patch_merge)

    temp_point_dem = os.path.join(TEMP_DIR, "temp_point_dem.shp")
    arcpy.sa.ExtractValuesToPoints(temp_point, dem, temp_point_dem)

    # run topo_to_raster using perimeter values from existing dem and height adjustment points
    value_field = "height"
    point_elevation = arcpy.sa.TopoPointElevation([[height_adj, value_field], [temp_point_dem, "RASTERVALU"]])
    out_ttr = arcpy.sa.TopoToRaster(point_elevation, cell_size=cell_size, data_type='SPOT')

    # apply mask
    arcpy.env.mask = patch_merge
    out_ttr += 0
    out_ttr.save(out_raster)
    arcpy.env.mask = None


arcpy.env.snapRaster = dem

patch_dem(patch_polygons=patch,
          height_adj=height_adjustment,
          dem=dem,
          out_raster=out_path)
