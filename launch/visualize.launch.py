from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription


def generate_launch_description():
    description_path = FindPackageShare("onshape_description")

    tf_prefix = LaunchConfiguration("tf_prefix")
    robot_description_content = Command(
        [
            "xacro ",
            PathJoinSubstitution([description_path, "urdf", "robot.urdf.xacro"]),
            " tf_prefix:='",
            tf_prefix,
            "'",
        ]
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[
            {
                "robot_description": ParameterValue(
                    robot_description_content, value_type=str
                )
            }
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
        arguments=["-d", str(description_path / "rviz" / "preview.rviz")],
    )

    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "tf_prefix",
                default_value="",
                description="Prefix for all link and joint names (e.g. 'left_').",
            ),
            robot_state_publisher_node,
            rviz_node,
            joint_state_publisher_gui_node,
        ]
    )
