import os
from typing import Dict, List
import typing
import arcpy
from arcpy import Parameter
from arcpy import ValueTable


class MergeConnectingTrails(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = (
            "Merge Connecting Trails (Designed for Rails to Trails OpenTrails Data)"
        )
        self.description = "Merges trails from the Rails to Trails Conservancy's OpenTrails data that are next to each other but not seen as a single multipart line. This tool currently is hardcoded to work with the Rails to Trails OpenTrails dataset and may need to be expanded to support generic line inputs."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        paramInput = arcpy.Parameter(
            displayName="Census Polygons",
            name="INPUT",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        paramOutput = arcpy.Parameter(
            displayName="Census Data",
            name="OUTPUT",
            datatype="GPFeatureLayer",
            multiValue=True,
            parameterType="Required",
            direction="Output",
        )
        paramOutput.parameterDependencies = [paramInput.name]

        params = [
            paramInput,
            paramOutput,
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters: List[Parameter]):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters: List[Parameter]):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters: List[Parameter], messages):
        """The source code of the tool."""
        arcpy.env.overwriteOutput = True

        # create a dictionary containing key-value pairs of the parameters
        # where the key is the param name and the value is the text value
        params = {}
        for elem in parameters:
            if elem.altered:
                params[elem.name] = elem.valueAsText

        arcpy.analysis.Buffer(
            params.get("INPUT"), "SC_T_Buffer", "2 Meters", "FULL", "ROUND"
        )

        arcpy.management.Dissolve(
            "SC_T_Buffer",
            "SC_T_Buffer__Dissolve",
            "",
            "",
            "SINGLE_PART",
            "DISSOLVE_LINES",
        )

        arcpy.management.AddField("SC_T_Buffer__Dissolve", "BUFFERID", "LONG")
        arcpy.management.CalculateField(
            "SC_T_Buffer__Dissolve", "BUFFERID", "!OBJECTID!"
        )

        # create a new fieldmappings
        fieldmappings = arcpy.FieldMappings()

        # add the BUFFERID field
        BUFFERID_field_map = arcpy.FieldMap()
        BUFFERID_field_map.addInputField("SC_T_Buffer__Dissolve", "BUFFERID")
        fieldmappings.addFieldMap(BUFFERID_field_map)

        # add the trails input feature classes
        fieldmappings.addTable(params.get("INPUT"))

        # delete
        if fieldmappings.findFieldMapIndex("ACCT_ID") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("ACCT_ID"))
        if fieldmappings.findFieldMapIndex("ACCT_TYPE") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("ACCT_TYPE"))
        if fieldmappings.findFieldMapIndex("ACCT_CLASS") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("ACCT_CLASS"))
        if fieldmappings.findFieldMapIndex("ACCT_CAT") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("ACCT_CAT"))
        if fieldmappings.findFieldMapIndex("Length_DMS") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("Length_DMS"))
        if fieldmappings.findFieldMapIndex("FY") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("FY"))
        if fieldmappings.findFieldMapIndex("DateAdded") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("DateAdded"))
        if fieldmappings.findFieldMapIndex("DateUpdated") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("DateUpdated"))
        if fieldmappings.findFieldMapIndex("STATUS") >= 0:
            fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex("STATUS"))

        for _fieldmap in fieldmappings:
            if _fieldmap.outputField.type == "String":
                index = fieldmappings.findFieldMapIndex(_fieldmap.outputField.name)
                fieldmap = fieldmappings.getFieldMap(index)

                fieldmap.mergeRule = "Join"
                fieldmap.joinDelimiter = ", "

                outputField = fieldmap.outputField
                outputField.length = 9999
                fieldmap.outputField = outputField

                fieldmappings.replaceFieldMap(index, fieldmap)

        arcpy.analysis.SpatialJoin(
            "SC_T_Buffer__Dissolve",
            params.get("INPUT"),
            "SC_T_B",
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            fieldmappings,
        )

        arcpy.topographic.PolygonToCenterline(
            in_features="SC_T_B",
            out_feature_class="SC_T_B__Centerline_Original",
            connecting_features=None,
        )

        arcpy.analysis.SpatialJoin(
            target_features="SC_T_B__Centerline_Original",
            join_features="SC_T_B",
            out_feature_class="SC_T_B__Centerline_BUFFERID",
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_ALL",
            field_mapping='BUFFERID "BUFFERID" true true false 255 Text 0 0,First,#,SC_T_B,BUFFERID,-1,-1',
            match_option="INTERSECT",
            search_radius=None,
            distance_field_name="",
        )

        arcpy.analysis.PairwiseDissolve(
            in_features="SC_T_B__Centerline_BUFFERID",
            out_feature_class="SC_T_B__Centerline_Dissolved",
            dissolve_field="BUFFERID",
            statistics_fields=None,
            multi_part="MULTI_PART",
        )

        arcpy.analysis.SpatialJoin(
            target_features="SC_T_B__Centerline_Dissolved",
            join_features="SC_T_B",
            out_feature_class=params.get("OUTPUT"),
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            field_mapping='BUFFERID "BUFFERID" true true false 255 Text 0 0,First,#,SC_T_B__Centerline_Dissolved,BUFFERID,0,255;SHAPE_Length "SHAPE_Length" false true true 8 Double 0 0,First,#,SC_T_B__Centerline_Dissolved,SHAPE_Length,-1,-1;Join_Count "Join_Count" true true false 4 Long 0 0,First,#,SC_T_B,Join_Count,-1,-1;TARGET_FID "TARGET_FID" true true false 4 Long 0 0,First,#,SC_T_B,TARGET_FID,-1,-1;BUFFERID_1 "BUFFERID" true true false 4 Long 0 0,First,#,SC_T_B,BUFFERID,-1,-1;SOURCE "SOURCE" true true false 9999 Text 0 0,First,#,SC_T_B,SOURCE,0,9999;QC "QC" true true false 9999 Text 0 0,First,#,SC_T_B,QC,0,9999;TRAIL_NAME "TRAIL_NAME" true true false 9999 Text 0 0,First,#,SC_T_B,TRAIL_NAME,0,9999;STATE "STATE" true true false 9999 Text 0 0,First,#,SC_T_B,STATE,0,9999;COUNTY "COUNTY" true true false 9999 Text 0 0,First,#,SC_T_B,COUNTY,0,9999;ORIG_FID "ORIG_FID" true true false 4 Long 0 0,First,#,SC_T_B,ORIG_FID,-1,-1;Shape_Length_1 "Shape_Length" false true true 8 Double 0 0,First,#,SC_T_B,Shape_Length,-1,-1;Shape_Area "Shape_Area" false true true 8 Double 0 0,First,#,SC_T_B,Shape_Area,-1,-1',
            match_option="INTERSECT",
            search_radius=None,
        )

        arcpy.management.Delete("SC_T_Buffer")
        arcpy.management.Delete("SC_T_Dissolve")
        arcpy.management.Delete("SC_T_Buffer__Dissolve")
        arcpy.management.Delete("SC_T_B")
        arcpy.management.Delete("SC_T_B__Centerline_Original")
        arcpy.management.Delete("SC_T_B__Centerline_BUFFERID")
        arcpy.management.Delete("SC_T_B__Centerline_Dissolved")

        arcpy.management.CalculateField(
            in_table=params.get("OUTPUT"),
            field="SOURCE",
            expression='", ".join([*set(!SOURCE!.split(", "))])',
        )
        arcpy.management.CalculateField(
            in_table=params.get("OUTPUT"),
            field="QC",
            expression='", ".join([*set(!QC!.split(", "))])',
        )
        arcpy.management.CalculateField(
            in_table=params.get("OUTPUT"),
            field="TRAIL_NAME",
            expression='", ".join([*set(!TRAIL_NAME!.split(", "))])',
        )
        arcpy.management.CalculateField(
            in_table=params.get("OUTPUT"),
            field="STATE",
            expression='", ".join([*set(!STATE!.split(", "))])',
        )
        arcpy.management.CalculateField(
            in_table=params.get("OUTPUT"),
            field="COUNTY",
            expression='", ".join([*set(!COUNTY!.split(", "))])',
        )
        arcpy.AddMessage("   ✅ Done")

        return

    def postExecute(self, parameters: List[Parameter]):
        """This method takes place after outputs are processed and
        added to the display."""
        return
