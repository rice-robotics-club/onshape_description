cmake_minimum_required(VERSION 3.8)
project(onshape_description)

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY urdf rviz launch DESTINATION share/${PROJECT_NAME})
# meshes/ only exists after the first Update URDF run
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/meshes)
  install(DIRECTORY meshes DESTINATION share/${PROJECT_NAME})
endif()

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
