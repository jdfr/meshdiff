import os,sys

if os.name=='posix':
  FREECADPATH = '/usr/lib/freecad/lib'
  sys.path.append(FREECADPATH)

import FreeCAD # this is needed to properly load FreeCAD libraries
import Mesh as m
import traceback

DEBUG = True
#DEBUG = False

inp  = sys.argv[1]
outp = sys.argv[2]

try:
  mesh = m.Mesh(str(inp))
  if (mesh.CountPoints<=0) or (mesh.CountFacets<=0):
    print "mesh file %s was incorrect or was an empty mesh" % inp
  else:
    mesh.write(str(outp))
except:
  if DEBUG: traceback.print_exc()
