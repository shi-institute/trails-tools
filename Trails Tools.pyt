import importlib

########################################################
# this convoluted way of importing the tools is required
# because ArcGIS does not reload imported modules
# unless the software is restarted

import SummarizeCensusAsBufferAlongLines

importlib.reload(SummarizeCensusAsBufferAlongLines)
from SummarizeCensusAsBufferAlongLines import (
    SummarizeCensusAsBufferAlongLines as SummarizeCensusAsBufferAlongLinesTool,
)

import MergeConnectingTrails

importlib.reload(MergeConnectingTrails)
from MergeConnectingTrails import MergeConnectingTrails as MergeConnectingTrailsTool

import ExtendLines

importlib.reload(ExtendLines)
from ExtendLines import ExtendLines as ExtendLinesTool

########################################################


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "TrailsTools"
        self.alias = "Trails Tools"

        # List of tool classes associated with this toolbox
        self.tools = [
            SummarizeCensusAsBufferAlongLinesTool,
            MergeConnectingTrailsTool,
            ExtendLinesTool,
        ]
