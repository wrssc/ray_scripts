import clr
import sys

clr.AddReference("System")
clr.AddReference(
    "C:Program Files\RaySearch Laboratories\RayStation 10A SP1\ScriptClient\ScriptClient.dll"
)

import ScriptClient


print("Running connect_to_raystation")
# Uncomment the following section to connect to RayStation
# -------------------------------------------------------
sys.path.append("C:Program Files\RaySearch Laboratories\RayStation 10A SP1")
sys.path.append("C:Program Files\RaySearch Laboratories\RayStation 10A SP1\ScriptClient")
# -------------------------------------------------------
