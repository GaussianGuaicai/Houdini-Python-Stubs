import sys,os
sys.path.append(os.path.abspath('.venv\Lib\site-packages'))

# # Mypy Stubgen
# from mypy.stubgen import main
# main(['-m','pdg','--parse-only','-o','output'])

# MonkeyType
import monkeytype
import pdg
with monkeytype.trace():
    path = ''
    tag = 'file/gg'
    file = pdg.File(path,True)