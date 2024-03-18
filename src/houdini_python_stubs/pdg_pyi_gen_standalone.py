import sys, os
os.environ['HFS'] = "C:\Program Files\Side Effects Software\Houdini 19.5.682"
os.environ['HHP'] = "C:\Program Files\Side Effects Software\Houdini 19.5.682\houdini\python3.9libs"

# == Set up the environment so that "import hou" works. ==
# Importing hou will load Houdini's libraries and initialize Houdini.
# This will cause Houdini to load any HDK extensions written in C++.
# These extensions need to link against Houdini's libraries,
# so the symbols from Houdini's libraries must be visible to other
# libraries that Houdini loads.  To make the symbols visible, we add the
# RTLD_GLOBAL dlopen flag.
if hasattr(sys, "setdlopenflags"):
    old_dlopen_flags = sys.getdlopenflags()
    sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)

# For Windows only.
# Add %HFS%/bin to the DLL search path so that Python can locate
# the hou module's Houdini library dependencies.  Note that 
# os.add_dll_directory() does not exist in older Python versions.
# Python 3.7 users are expected to add %HFS%/bin to the PATH environment
# variable instead prior to launching Python.
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    os.add_dll_directory("{}/bin".format(os.environ["HFS"]))

try:
    import hou
except ImportError:
    # If the hou module could not be imported, then add 
    # $HFS/houdini/pythonX.Ylibs to sys.path so Python can locate the
    # hou module.
    sys.path.append(os.environ['HHP'])
    import hou
finally:
    # Reset dlopen flags back to their original value.
    if hasattr(sys, "setdlopenflags"):
        sys.setdlopenflags(old_dlopen_flags)

import pdg

import pybind11_stubgen as stubgen
import re

def regex(pattern_str: str) -> re.Pattern:
    try:
        return re.compile(pattern_str)
    except re.error as e:
        raise ValueError(f"Invalid REGEX pattern: {e}")

def regex_colon_path(regex_path: str) -> tuple[re.Pattern, str]:
    pattern_str, path = regex_path.rsplit(":", maxsplit=1)
    if any(not part.isidentifier() for part in path.split(".")):
        raise ValueError(f"Invalid PATH: {path}")
    return regex(pattern_str), path

enum_class_locations = (
    'workItemState:_pdg.workItemState',
    'attribSaveType:_pdg.attribSaveType',
    'dirtyHandlerType:_pdg.dirtyHandlerType',
    'cookType:_pdg.cookType',
    'attribErrorLevel:_pdg.attribErrorLevel',
    'attribOverwrite:_pdg.attribOverwrite',
    'attribType:_pdg.attribType',
    'attribMatchType:_pdg.attribMatchType',
    'pathMapMatchType:_pdg.pathMapMatchType',
    'attribCollisionStrategy:_pdg.attribCollisionStrategy',
    'fileTransferType:_pdg.fileTransferType'
)
enum_class_locations = map(lambda string: regex_colon_path(string),enum_class_locations)

stubgen.main(module_name='_pdg',output_dir='output',enum_class_locations=list(enum_class_locations))

# sys.argv = [
#     '--enum-class-locations workItemState:pdg.workItemState',
#     '-o output',
#     '_pdg'
#     ]
# stubgen.main()
# print('done')