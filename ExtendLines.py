import os
from typing import Dict, List
import typing
import arcpy
from arcpy import Parameter
from arcpy import ValueTable
from math import hypot
import collections
from operator import add


class ExtendLines(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Extend Lines"
        self.description = "Extends input lines by a specified distance. Distances can be positive or negative."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        paramPolylineLayer = arcpy.Parameter(
            displayName="Polyline Layer (modified by this tool)",
            name="INPUT_POLYLINE_LAYER",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        paramDistance = arcpy.Parameter(
            displayName="Distance To Extend Line",
            name="INPUT_LINE_EXTEND_DISTANCE",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )

        paramBothDirections = arcpy.Parameter(
            displayName="Extend in Both Directions",
            name="INPUT_EXTEND_BOTH_DIRECTIONS",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input",
        )
        paramBothDirections.value = False

        params = [
            paramPolylineLayer,
            paramDistance,
            paramBothDirections,
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

        # adapted from https://gis.stackexchange.com/questions/71645/extending-line-by-specified-distance-in-arcgis-for-desktop

        layer = params.get("INPUT_POLYLINE_LAYER")
        extend_distance = params.get("INPUT_LINE_EXTEND_DISTANCE")
        extend_both_directions = params.get("INPUT_EXTEND_BOTH_DIRECTIONS")

        distance = float(extend_distance.split()[0])
        unit = extend_distance.split()[1]

        linearUnit = arcpy.Describe(layer).spatialReference.linearUnitName

        if linearUnit == "Foot_US" and unit == "Meters":
            distance *= 3.2808399
        elif linearUnit == "Meter" and unit == "Feet":
            distance *= 0.3048006096012192

        # Computes new coordinates x3,y3 at a specified distance
        # along the prolongation of the line from x1,y1 to x2,y2
        def newcoord(coords, dist):
            (x1, y1), (x2, y2) = coords
            dx = x2 - x1
            dy = y2 - y1
            linelen = hypot(dx, dy)

            x3 = x2 + dx / linelen * dist
            y3 = y2 + dy / linelen * dist
            return x3, y3

        # accumulate([1,2,3,4,5]) --> 1 3 6 10 15
        # Equivalent to itertools.accumulate() which isn't present in Python 2.7
        def accumulate(iterable):
            it = iter(iterable)
            total = next(it)
            yield total
            for element in it:
                total = add(total, element)
                yield total

        def extend_line(input_layer):
            # OID is needed to determine how to break up flat list of data by feature.
            coordinates = [
                [row[0], row[1]]
                for row in arcpy.da.SearchCursor(
                    input_layer, ["OID@", "SHAPE@XY"], explode_to_points=True
                )
            ]

            oid, vert = zip(*coordinates)

            # Construct list of numbers that mark the start of a new feature class.
            # This is created by counting OIDS and then accumulating the values.
            vertcounts = list(accumulate(collections.Counter(oid).values()))

            # Grab the last two vertices of each feature
            lastpoint = [
                point
                for x, point in enumerate(vert)
                if x + 1 in vertcounts or x + 2 in vertcounts
            ]

            # Convert flat list of tuples to list of lists of tuples.
            # Obtain list of tuples of new end coordinates.
            newvert = [newcoord(y, distance) for y in zip(*[iter(lastpoint)] * 2)]

            j = 0
            with arcpy.da.UpdateCursor(
                input_layer, "SHAPE@XY", explode_to_points=True
            ) as rows:
                for i, row in enumerate(rows):
                    if i + 1 in vertcounts:
                        row[0] = newvert[j]
                        j += 1
                        rows.updateRow(row)

        extend_line(layer)

        if extend_both_directions:
            arcpy.FlipLine_edit(layer)
            extend_line(layer)
            arcpy.FlipLine_edit(layer)

        return

    def postExecute(self, parameters: List[Parameter]):
        """This method takes place after outputs are processed and
        added to the display."""
        return
