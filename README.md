# onshape_description

This repository contains a template for a ROS2 robot description package. By convention, ROS2 packages
that exist solely to house a robot's URDF files and CAD meshes are usually titled "[robot name]_description".
These packages can be as simple as a single urdf file, but often include additional features, such as a launch file to preview the robot URDF (as this template provides). Overall, this repository is meant to exist
as a convention for our robot description packages.

## Features
This template includes the following features:

1. Copying the URDF file and meshes to `install/` on a `colcon build`.
2. Previewing the urdf file with rviz2.
3. Loading in the urdf file from an Onshape assembly via [onshape-to-robot](https://onshape-to-robot.readthedocs.io/en/latest/index.html).
4. Specifying a joint name array as a python package.

### rviz2

The URDF model can be previewed in rviz2 by running this launch file:
```bash
ros2 launch servobot_description visualize.launch.py
```

### onshape-to-robot

This package provides the github action workflow `.github/workflows/update-urdf.yaml`,
which updates the contents of the package from the Onshape assembly specified in `config.json`. 
This can be run by going to the Actions tab, going to the Update URDF action, clicking on "run workflow", 
and specifying the main branch. The corresponding Onshape assembly document should be in the Rice Robotics Club
organization, as the API key used for fetching the files from Onshape are stored in the GitHub organization's secrets.
This allows anyone to perform this operation as members of the GitHub organization, without needing to obtain an API key.

In order for the import to work properly, the Onshape assembly needs to comply with the onshape-to-robot tool's joint name scheme.
This is specified in the documentation [here](https://onshape-to-robot.readthedocs.io/en/latest/design.html). The main requirement 
is that all mates corresponding to a URDF joint need to be named according to `dof_[joint name]`. There are additional features
that may be used, such as for handling kinematic loops.

### Python Joint Names

A joint name array constant is included asa python package, which can be imported via:
```Python
from onshape_description import JOINT_NAMES
```

## Usage
In order to extend from this template repository, the package name, robot name, and Onshape information need to be specified in the following files.

1. In `package.xml`:

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>onshape_description</name> <!-- TODO: replace with package name -->
  <version>1.0.0</version>
  
...
```

2. In `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.8)
project(onshape_description_template) # TODO: replace with package name

...
```

3. In `config.json`, specify the robot name, package name, as well as the Onshape document, workspace, and element ids, along with the assembly name:
```json
{
  "robot_name": "robot", # TODO: replace with robot name
  "package_name": "onshape_description", # TODO: replace with package name
  "assets_directory": "meshes",
  "output_filename": "urdf/robot",
  "output_format": "urdf",
  "document_id": "", # TODO: insert document_id (after d/ in url)
  "workspace_id": "", # TODO: insert workspace_id (after w/ in url)
  "element_id": "", # TODO: insert element_id (after e/ in url)
  "assembly_name": "" # TODO: insert OnShape assembly name
}
```

4. In `launch/visualize.launch.py`:
```python
...

def generate_launch_description():
    description_path = get_package_share_path("onshape_description") # TODO: replace with package name

    robot_description_content = Command(["cat ", str(description_path / "urdf" / "robot.urdf")])

...
```

5. Rename `onshape_description/` to the new package name.

6. In `onshape_description/__init__.py`, specify the URDF's joint names:

```python
JOINT_NAMES = [
	"" # TODO: add all URDF joint names
]
```

All done!
