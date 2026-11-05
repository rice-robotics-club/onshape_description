"""Tests for scripts/urdf_to_xacro.py.

Run with ``python3 -m pytest test`` (or ``python3 -m unittest discover test``). Requires the
``xacro`` Python package (``pip install xacro`` or ROS 2's ros-<distro>-xacro). Tests that call
``check_urdf`` (liburdfdom-tools) are skipped if it is not installed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "urdf_to_xacro.py"
FIXTURE = REPO / "test" / "fixtures" / "sample_robot.urdf"
EXPECTED_LINKS = {"chassis", "camera", "finger_left", "finger_right"}
EXPECTED_JOINTS = {"base_joint", "camera_frame", "finger_left", "finger_right"}


def convert(urdf: Path, output_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(urdf), "-o", str(output_dir)],
        check=True, capture_output=True, text=True,
    )


def expand(xacro_file: Path, **mappings: str) -> str:
    args = [f"{key}:={value}" for key, value in mappings.items()]
    return subprocess.run(
        [sys.executable, "-c", "import xacro; xacro.main()", str(xacro_file), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def check_urdf(urdf_xml: str, directory: Path) -> None:
    if shutil.which("check_urdf") is None:
        return
    path = directory / "expanded.urdf"
    path.write_text(urdf_xml)
    subprocess.run(["check_urdf", str(path)], check=True, capture_output=True, text=True)


def names(urdf_xml: str, tag: str) -> set[str]:
    return {element.get("name") for element in ET.fromstring(urdf_xml).findall(tag)}


class UrdfToXacroTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.result = convert(FIXTURE, self.tmp)
        self.top_level = self.tmp / "sample_robot.urdf.xacro"
        self.macro = self.tmp / "sample_robot_macro.xacro"

    def test_outputs_exist(self) -> None:
        self.assertTrue(self.top_level.is_file())
        self.assertTrue(self.macro.is_file())

    def test_expands_without_prefix(self) -> None:
        urdf = expand(self.top_level)
        check_urdf(urdf, self.tmp)
        self.assertEqual(names(urdf, "link"), EXPECTED_LINKS | {"world"})
        self.assertEqual(names(urdf, "joint"), EXPECTED_JOINTS)

    def test_expands_with_prefix(self) -> None:
        urdf = expand(self.top_level, tf_prefix="r1_")
        check_urdf(urdf, self.tmp)
        root = ET.fromstring(urdf)
        self.assertEqual(names(urdf, "link"), {f"r1_{n}" for n in EXPECTED_LINKS} | {"world"})
        self.assertEqual(names(urdf, "joint"), {f"r1_{n}" for n in EXPECTED_JOINTS})
        self.assertEqual(root.find("joint/mimic").get("joint"), "r1_finger_left")
        self.assertTrue(all(m.get("name").startswith("r1_") for m in root.iter("material")))

    def test_attaches_root_link_to_parent(self) -> None:
        urdf = ET.fromstring(expand(self.top_level, tf_prefix="r1_"))
        joint = next(j for j in urdf.findall("joint") if j.get("name") == "r1_base_joint")
        self.assertEqual(joint.get("type"), "fixed")
        self.assertEqual(joint.find("parent").get("link"), "world")
        self.assertEqual(joint.find("child").get("link"), "r1_chassis")
        self.assertIsNotNone(joint.find("origin"))

    def test_dummy_base_link_is_stripped(self) -> None:
        self.assertIn("removed the dummy base_link", self.result.stderr)
        self.assertNotIn("base_link", self.macro.read_text())

    def test_limits_are_preserved(self) -> None:
        urdf = ET.fromstring(expand(self.top_level))
        limit = next(j for j in urdf.findall("joint") if j.get("name") == "finger_left").find("limit")
        self.assertEqual(dict(limit.attrib), {"effort": "20", "velocity": "0.5", "lower": "0", "upper": "0.04"})

    def test_two_instances_coexist(self) -> None:
        scene = self.tmp / "scene.urdf.xacro"
        scene.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="scene">
              <xacro:include filename="sample_robot_macro.xacro"/>
              <link name="world"/>
              <xacro:sample tf_prefix="left_" parent="world">
                <origin xyz="0 0.5 0" rpy="0 0 0"/>
              </xacro:sample>
              <xacro:sample tf_prefix="right_" parent="world">
                <origin xyz="0 -0.5 0" rpy="0 0 0"/>
              </xacro:sample>
            </robot>
            """))
        urdf = expand(scene)
        check_urdf(urdf, self.tmp)
        links = [l.get("name") for l in ET.fromstring(urdf).findall("link")]
        self.assertEqual(len(links), len(set(links)))
        self.assertEqual(len(links), 2 * len(EXPECTED_LINKS) + 1)

    def test_is_idempotent(self) -> None:
        first = (self.macro.read_text(), self.top_level.read_text())
        convert(FIXTURE, self.tmp)
        self.assertEqual(first, (self.macro.read_text(), self.top_level.read_text()))

    def test_dummy_references_follow_root_link(self) -> None:
        root = ET.fromstring(expand(self.top_level, tf_prefix="r1_"))
        self.assertEqual([g.get("reference") for g in root.findall("gazebo")], ["r1_chassis", "r1_chassis"])

    def test_dollar_signs_stay_literal(self) -> None:
        root = ET.fromstring(expand(self.top_level))
        self.assertEqual(root.find("gazebo/plugin").text, "echo $(HOME) ${x}")

    def modified_fixture(self, name: str, edit) -> Path:
        robot = ET.parse(FIXTURE).getroot()
        edit(robot)
        path = self.tmp / f"{name}.urdf"
        ET.ElementTree(robot).write(path)
        return path

    def test_rejects_invalid_macro_names(self) -> None:
        for bad in ("2024_bot", "my robot", "bot.v2", "include", "if"):
            path = self.modified_fixture("bad_name", lambda robot: robot.set("name", bad))
            with self.subTest(name=bad), self.assertRaises(subprocess.CalledProcessError) as error:
                convert(path, self.tmp / "bad")
            self.assertIn("robot_name", error.exception.stderr)

    def test_rejects_link_named_world(self) -> None:
        path = self.modified_fixture(
            "world_link", lambda robot: robot.find("link[@name='camera']").set("name", "world")
        )
        with self.assertRaises(subprocess.CalledProcessError) as error:
            convert(path, self.tmp / "world")
        self.assertIn("'world'", error.exception.stderr)

    def test_keeps_base_link_with_geometry(self) -> None:
        robot = ET.parse(FIXTURE).getroot()
        base = robot.find("link[@name='base_link']")
        ET.SubElement(ET.SubElement(base, "visual"), "geometry").append(ET.Element("box", {"size": "1 1 1"}))
        urdf_path = self.tmp / "real_base.urdf"
        ET.ElementTree(robot).write(urdf_path)
        out = self.tmp / "real_base"
        convert(urdf_path, out)
        urdf = expand(out / "real_base.urdf.xacro")
        self.assertIn("base_link", names(urdf, "link"))


if __name__ == "__main__":
    unittest.main()
