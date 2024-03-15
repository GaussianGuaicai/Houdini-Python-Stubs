import sys,os
sys.path.append(os.path.abspath('.venv\Lib\site-packages'))

# os.environ['HFS'] = "C:\Program Files\Side Effects Software\Houdini 19.5.682"
# os.environ['HHP'] = "C:\Program Files\Side Effects Software\Houdini 19.5.682\houdini\python3.9libs"
# def enableHouModule():
#     '''Set up the environment so that "import hou" works.'''
#     import sys, os

#     # Importing hou will load Houdini's libraries and initialize Houdini.
#     # This will cause Houdini to load any HDK extensions written in C++.
#     # These extensions need to link against Houdini's libraries,
#     # so the symbols from Houdini's libraries must be visible to other
#     # libraries that Houdini loads.  To make the symbols visible, we add the
#     # RTLD_GLOBAL dlopen flag.
#     if hasattr(sys, "setdlopenflags"):
#         old_dlopen_flags = sys.getdlopenflags()
#         sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)

#     # For Windows only.
#     # Add %HFS%/bin to the DLL search path so that Python can locate
#     # the hou module's Houdini library dependencies.  Note that 
#     # os.add_dll_directory() does not exist in older Python versions.
#     # Python 3.7 users are expected to add %HFS%/bin to the PATH environment
#     # variable instead prior to launching Python.
#     if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
#         os.add_dll_directory("{}/bin".format(os.environ["HFS"]))

#     try:
#         import hou
#     except ImportError:
#         # If the hou module could not be imported, then add 
#         # $HFS/houdini/pythonX.Ylibs to sys.path so Python can locate the
#         # hou module.
#         sys.path.append(os.environ['HHP'])
#         import hou
#     finally:
#         # Reset dlopen flags back to their original value.
#         if hasattr(sys, "setdlopenflags"):
#             sys.setdlopenflags(old_dlopen_flags)
# enableHouModule()

# # Mypy Stubgen
# from mypy.stubgen import main
# from mypy import stubgenc
# main(['-m','hou','--ignore-errors','-o','output'])

import hou
import pdg

# MonkeyType
import monkeytype
from monkeytype.config import Config,DefaultConfig
class PDG_Config(DefaultConfig):
    def max_typed_dict_size(self) -> int:
        return 10

config = PDG_Config()
with monkeytype.trace(config):
    path = 'test.py'
    tag = 'file/gg'
    pdg.File(path,True)
    
    pdg_workitem_dict = dir(pdg.WorkItem)

    net = hou.node('/obj')
    new_node = net.createNode('geo')
    new_node.name()