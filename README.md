# onshape_description

This repository contains a template for a ROS2 robot description package. By convention, ROS2 packages
that exist solely to house a robot's URDF files and CAD meshes are usually titled "[robot name]_description".
These packages can be as simple as a single urdf file, but often include additional features, such as a launch file to preview the robot URDF (as this template provides). Overall, this repository is meant to exist
as a convention for our robot description packages.

**Rice Robotics Members!!!** In order for the attached workflow to work, you must create a *public* repository, as the OnShape API key is stored in our organization's secrets, which can only be accessed by a GitHub actions workflow in a public repository.

## Features
This template includes the following features:

1. Copying the URDF/xacro files and meshes to `install/` on a `colcon build`.
2. Previewing the robot with rviz2.
3. Loading in the urdf file from an Onshape assembly via [onshape-to-robot](https://onshape-to-robot.readthedocs.io/en/latest/index.html).
4. Generating a reusable xacro macro (with a `tf_prefix` and `parent` link) from that URDF.
5. Specifying a joint name array as a python package.

### rviz2

The robot can be previewed in rviz2 by running this launch file:
```bash
ros2 launch onshape_description visualize.launch.py
# optionally prefix every link/joint name:
ros2 launch onshape_description visualize.launch.py tf_prefix:=left_
```

### onshape-to-robot

This package provides the github action workflow `.github/workflows/update-urdf.yml`,
which updates the contents of the package from the Onshape assembly specified in `config.json`. 
This can be run by going to the Actions tab, going to the Update URDF action, clicking on "run workflow", 
and specifying the main branch. The corresponding Onshape assembly document should be in the Rice Robotics Club
organization, as the API key used for fetching the files from Onshape are stored in the GitHub organization's secrets.
This allows anyone to perform this operation as members of the GitHub organization, without needing to obtain an API key.

In order for the import to work properly, the Onshape assembly needs to comply with the onshape-to-robot tool's joint name scheme.
This is specified in the documentation [here](https://onshape-to-robot.readthedocs.io/en/latest/design.html). The main requirement 
is that all mates corresponding to a URDF joint need to be named according to `dof_[joint name]`. There are additional features
that may be used, such as for handling kinematic loops.

Joint limits come from the limits set on the Onshape mates (unless `"ignore_limits": true`), and can be
overridden per joint, together with `max_effort` and `max_velocity`, using `joint_properties` in `config.json`
(see the [URDF exporter docs](https://onshape-to-robot.readthedocs.io/en/latest/exporter_urdf.html)).
They are copied unchanged into the xacro files.

### Xacro

After every export, `scripts/urdf_to_xacro.py` turns `urdf/robot.urdf` into two files, following the
[Universal Robots description](https://github.com/UniversalRobots/Universal_Robots_ROS2_Description) convention:

* `urdf/robot_macro.xacro` defines a macro named after `robot_name` in `config.json`, taking
  `tf_prefix parent *origin`. Every link, joint and material name gets `${tf_prefix}` in front of it, and the
  robot's root link is attached to `parent` through a fixed `${tf_prefix}base_joint` placed at `origin`.
* `urdf/robot.urdf.xacro` is the standalone description: it defines a dummy `world` link and instantiates the
  macro on it. This is what `visualize.launch.py` loads.

`urdf/robot.urdf` is kept as the plain, unprefixed URDF for tools that don't read xacro (e.g. MuJoCo).
Leave `add_dummy_base_link` off in `config.json`: the dummy link belongs in the top-level `.urdf.xacro`
(the script removes onshape-to-robot's one if it is present). `ros2_control` tags are intentionally not
generated; add them in a separate package.

To use the robot in another description (for example, two copies in one scene):
```xml
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="scene">
  <xacro:include filename="$(find onshape_description)/urdf/robot_macro.xacro"/>
  <link name="world"/>
  <xacro:robot tf_prefix="left_" parent="world">
    <origin xyz="0 0.5 0" rpy="0 0 0"/>
  </xacro:robot>
  <xacro:robot tf_prefix="right_" parent="world">
    <origin xyz="0 -0.5 0" rpy="0 0 0"/>
  </xacro:robot>
</robot>
```
(Replace `xacro:robot` with `xacro:<robot_name>`.) Don't edit the generated xacro files by hand; they are
overwritten on every export, and the Test workflow fails if they don't match `urdf/robot.urdf`. To
regenerate them locally, run `python3 scripts/urdf_to_xacro.py`. Tests for the script live in `test/` and run with
`python3 -m pytest test` (needs `pip install xacro pytest`).

### Python Joint Names

A joint name array constant is included as a python package, which can be imported via:
```Python
from onshape_description import JOINT_NAMES
```

## Usage
In order to extend from this template repository, the package name, robot name, and Onshape information need to be specified in the following files.

1. In `config.json`, specify the Onshape document, workspace, and element ids, along with the assembly name.
   Set `robot_name` to something unique made of letters, digits and underscores (not starting with a digit), since it becomes the xacro macro name. Keep `package_name` equal to this
   package's name so mesh paths resolve as `package://<package_name>/meshes/...`:
```json
{
  "robot_name": "robot",
  "package_name": "onshape_description",
  "assets_directory": "meshes",
  "output_filename": "robot",
  "output_format": "urdf",
  "document_id": "", # TODO: insert document_id (after d/ in url)
  "workspace_id": "", # TODO: insert workspace_id (after w/ in url)
  "element_id": "", # TODO: insert element_id (after e/ in url)
  "assembly_name": "" # TODO: insert OnShape assembly name
}
```

2. In `onshape_description/__init__.py`, specify the URDF's joint names:

```python
JOINT_NAMES = [
	"" # TODO: add all URDF joint names
]
```

All done!
