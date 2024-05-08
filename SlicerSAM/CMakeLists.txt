cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SAM3D)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/shizoda/SlicerSAM")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Hirohisa Oda (University of Shizuoka)")
set(EXTENSION_DESCRIPTION "Interactive GUI for SAM-Med3D")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/SAM3D.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/SAM3D/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SAM)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
