import os
from typing import Dict, List
import typing
import arcpy
from arcpy import Parameter
from arcpy import ValueTable


class SummarizeCensusAsBufferAlongLines(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Summarize Census As Buffer Along Lines"
        self.description = "Creates centroids for census areas and summarizes chosen attributes to a buffer around the input feature class."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        paramCensus = arcpy.Parameter(
            displayName="Census Polygons",
            name="INPUT_CENSUS",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        paramCensusData = arcpy.Parameter(
            displayName="Census Data",
            name="INPUT_CENSUS_DATA",
            datatype="GPTableView",
            multiValue=True,
            parameterType="Required",
            direction="Input",
        )

        paramLines = arcpy.Parameter(
            displayName="Lines",
            name="INPUT_LINES",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        paramBufferDistance = arcpy.Parameter(
            displayName="Buffer Distance",
            name="INPUT_BUFFER_DISTANCE",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )
        paramBufferDistance.value = "1 Kilometers"

        paramBufferDissolve = arcpy.Parameter(
            displayName="Buffer Dissolve Field",
            name="INPUT_BUFFER_DISSOLVE",
            datatype="Field",
            parameterType="Optional",
            direction="Input",
        )
        paramBufferDissolve.parameterDependencies = [paramLines.name]

        paramCensusFields = arcpy.Parameter(
            displayName="Summary Fields",
            name="INPUT_SUMMARY_FIELDS",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input",
        )
        paramCensusFields.parameterDependencies = [paramCensusData.name]
        paramCensusFields.columns = [
            ["Field", "Field"],
            ["GPString", "Label"],
            ["GPString", "Statistic Type"],
        ]
        paramCensusFields.filters[2].type = "ValueList"
        paramCensusFields.filters[2].list = ["SUM", "MEAN", "MIN", "MAX", "STDEV"]

        paramSummaryBuffer = arcpy.Parameter(
            displayName="Summary Buffer",
            name="OUTPUT_SUMMARY_BUFFER",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )
        paramSummaryBuffer.value = "SummaryBuffer"

        paramCentroids = arcpy.Parameter(
            displayName="Centroids",
            name="OUTPUT_I_CENTROIDS",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output",
            category="Intermediate Outputs",
        )

        params = [
            paramCensus,
            paramCensusData,
            paramLines,
            paramBufferDistance,
            paramBufferDissolve,
            paramCensusFields,
            paramSummaryBuffer,
            paramCentroids,
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters: List[Parameter]):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # make the output summary buffer file name match the census polygons
        # name, but with __SummaryBuffer added to the end
        if parameters[2].valueAsText:
            census_shape_name = os.path.splitext(parameters[2].valueAsText)[0]
            if os.path.sep in parameters[2].valueAsText:
                census_shape_name = census_shape_name.split(os.path.sep)[-1]

            parameters[6].value = f"{census_shape_name}__SummaryBuffer"

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

        arcpy.SetProgressorLabel("Buffering lines...")
        arcpy.AddMessage("⏳ Buffering input lines...")
        if params.get("INPUT_BUFFER_DISSOLVE"):
            arcpy.AddMessage(
                "   ⌛ Creating buffer with dissolve (this may take a very long time)..."
            )
        else:
            arcpy.AddMessage("   ⌛ Creating buffer...")
        arcpy.analysis.Buffer(
            in_features=params.get("INPUT_LINES"),
            out_feature_class="TrailsBuffer",
            buffer_distance_or_field=params.get("INPUT_BUFFER_DISTANCE"),
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="LIST" if params.get("INPUT_BUFFER_DISSOLVE") else None,
            dissolve_field=params.get("INPUT_BUFFER_DISSOLVE"),
            method="PLANAR",
        )
        arcpy.AddMessage("   ✅ Done")

        arcpy.SetProgressorLabel("Identifying census areas intersected by lines...")
        arcpy.AddMessage("⏳ Identifying census areas intersected by lines...")
        arcpy.AddMessage("   ⌛ Indentifying...")
        arcpy.analysis.SpatialJoin(
            target_features=params.get("INPUT_CENSUS"),
            join_features="TrailsBuffer",
            out_feature_class="LinesIntersectionSpatialJoin",
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_ALL",
            field_mapping=None,
            match_option="INTERSECT",
        )

        arcpy.SetProgressorLabel("Saving census areas intersected by lines...")
        arcpy.AddMessage("   ⌛ Exporting to new feature class...")
        arcpy.conversion.ExportFeatures(
            in_features="LinesIntersectionSpatialJoin",
            out_features="LinesIntersectionAreaPlain",
            where_clause="Join_Count > 0",
            use_field_alias_as_name="NOT_USE_ALIAS",
            field_mapping=None,
            sort_field=None,
        )

        arcpy.SetProgressorLabel(
            "Adding census details to census areas intersected by lines..."
        )
        arcpy.AddMessage("   ⌛ Adding census details...")
        arcpy.analysis.SpatialJoin(
            target_features="LinesIntersectionAreaPlain",
            join_features=params.get("INPUT_CENSUS"),
            out_feature_class="LinesIntersectionArea",
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            match_option="INTERSECT",
        )
        arcpy.AddMessage("   ✅ Done")

        arcpy.SetProgressorLabel("Creating centroids...")
        arcpy.AddMessage("⏳ Creating centroids for census areas...")
        arcpy.AddMessage("   ⌛ Creating centroids...")
        centroids_layer = (
            params.get("OUTPUT_I_CENTROIDS")
            if params.get("OUTPUT_I_CENTROIDS")
            else "LinesIntersectionAreaCentroids"
        )
        arcpy.management.FeatureToPoint(
            in_features="LinesIntersectionArea",
            out_feature_class=centroids_layer,
            point_location="CENTROID",
        )

        arcpy.AddMessage("   ⌛ Combining data tables (this may take a while)...")
        census_data_tables: List[str] = (
            params.get("INPUT_CENSUS_DATA").replace("'", "").replace('"', "").split(";")
        )
        for index, table_path in enumerate(census_data_tables):
            if index == 0:
                arcpy.MakeTableView_management(table_path, "CensusTableView")
            else:
                arcpy.MakeTableView_management(table_path, f"CensusTableView{index}")
                arcpy.conversion.TableToTable(  # this ensures that tables have unique names
                    f"CensusTableView{index}", out_name=f"CensusTable{index}"
                )
                arcpy.AddJoin_management(
                    in_layer_or_view="CensusTableView",
                    in_field="GISJOIN",
                    join_table=f"CensusTable{index}",
                    join_field="GISJOIN",
                    join_type="KEEP_ALL",
                )

        arcpy.SetProgressorLabel("Mapping fields...")
        arcpy.AddMessage("   ⌛ Preparing summary fields to be joined...")
        fieldmappings = arcpy.FieldMappings()
        summary_fields: ValueTable = parameters[5].value
        for info in summary_fields:
            field_name = info[0]
            field_label = info[1]
            statistic = info[2]

            field_map = arcpy.FieldMap()
            field_map.addInputField("CensusTableView", field_name)

            arcpy.AddMessage(field_map)
            outputField = field_map.outputField
            outputField.aliasName = field_label
            field_map.outputField = outputField

            fieldmappings.addFieldMap(field_map)

        arcpy.SetProgressorLabel("Joining fields...")
        arcpy.AddMessage(
            "   ⌛ Joining summary fields to centroids (this may take a while)..."
        )
        arcpy.AddMessage("         Using field mappings:")
        arcpy.AddMessage(f"         {fieldmappings.exportToString()}")
        arcpy.management.JoinField(
            in_data=centroids_layer,
            in_field="GISJOIN",
            join_table="CensusTableView",
            join_field="GISJOIN",
            fields=None,
            fm_option="USE_FM",
            field_mapping=fieldmappings,
        )
        arcpy.AddMessage("   ✅ Done")

        arcpy.SetProgressorLabel("Summarizing to buffer...")
        arcpy.AddMessage("⌛ Summarizing centroids to buffer...")
        arcpy.AddMessage("   ⌛ Preparing summary fields...")
        summary_fields_str = ""
        for info in summary_fields:
            field_name = info[0]
            statistic = info[2]
            summary_fields_str += f"{field_name} {statistic};"
        arcpy.AddMessage("   ⌛ Summarizing...")
        arcpy.AddMessage(
            f'         Using summary field configuration: "{summary_fields_str}"'
        )
        arcpy.analysis.SummarizeWithin(
            in_polygons="TrailsBuffer",
            in_sum_features=centroids_layer,
            out_feature_class=params.get("OUTPUT_SUMMARY_BUFFER"),
            keep_all_polygons="KEEP_ALL",
            sum_fields=summary_fields_str,
            sum_shape="ADD_SHAPE_SUM",
            shape_unit="SQUAREKILOMETERS",
            group_field=None,
            add_min_maj="NO_MIN_MAJ",
            add_group_percent="NO_PERCENT",
            out_group_table=None,
        )
        arcpy.AddMessage("   ✅ Done")

        return

    def postExecute(self, parameters: List[Parameter]):
        """This method takes place after outputs are processed and
        added to the display."""
        return
