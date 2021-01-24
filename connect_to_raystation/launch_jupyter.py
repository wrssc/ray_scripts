import os
import sys
from pathlib import Path
import statetree
import getpass
import datetime
import shutil
import inspect

statetree.RunStateTree()


def get_python_scripts_path():
    for p in sys.path:
        if "site-packages" in p.lower():

            # We know site-packages is in "p", but we may have grabbed a path
            # that does not have site-packages at the stem.
            # We want path-to-python/lib/site-packages
            p = Path(p)
            while p.stem != "site-packages":
                p = p.parent

            # Now we care return path-to-python/Scripts
            return p.parent.parent / "Scripts"


# Determine the directory from which this script is being run.
# This is not trivial due to the way ray_scripts runs a script. If the script
# is being run from a dev distribution, it's location will differ each time it
# is run.
script_path = inspect.getframeinfo(inspect.currentframe()).filename
connect_to_raystation_path = Path(script_path).parent

# Generate a filename
user = getpass.getuser()
now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
notebook_name = f"{user}_{now}.ipynb"

# Define paths to jupyter, web browser and notebook file
script_path = get_python_scripts_path()
jupyter_path = script_path / "jupyter-notebook.exe"
browser_path = Path("C:\\Program Files\\Internet Explorer\\iexplore.exe")
notebook_root = Path("Q:\\RadOnc\\RayStation\\RayScripts\\JupyterNotebooks")
notebook_path = notebook_root / notebook_name
template_path = notebook_root / "Templates" / "ConnectToRayStation.ipynb"

# Copy the template to the notebook root:
shutil.copyfile(src=template_path, dst=notebook_path)

command_str = f'set RAYSTATION_PID={sys.argv[1]}'
command_str += f' & set BROWSER="{str(browser_path)}"'
command_str += f' & "{str(jupyter_path)}" "{str(notebook_path)}"'
command_str += f' --browser="{str(browser_path)}" %s'
print(f"Running: {command_str}")

os.system(command_str)
