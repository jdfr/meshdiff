import numpy as n
import os.path as op
import os
import subprocess as sub
#import scipy.spatial.distance as sp
from scipy.spatial import Delaunay
import traceback
import collections as cols

DEBUG    = True
NOTDEBUG = not DEBUG

#return values are of this type for easy coding
class RetVal(cols.namedtuple('RetVal', ['ok', 'val', 'argnum', 'errcode'])):
    def __new__(cls, ok=None, val=None, argnum=None, errcode=None):
        return super(RetVal, cls).__new__(cls, ok, val, argnum, errcode)

freecadscript = op.join(op.dirname(op.realpath(__file__)), 'freecadscript.py')

#this should be a parameter, but we will keep it a hardcoded choice while it is not necessary
meshmode = 'cork'
#meshmode = 'openscad'

if   os.name=='posix':
  toolpaths = {
    'cork':      op.join(op.dirname(op.realpath(__file__)), 'cork'),
    'openscad': 'openscad',
    'meshlab':  'meshlabserver',
    'freecadp': 'python'
  }
elif os.name=='nt':
  toolpaths = {
    'cork':      op.join(op.dirname(op.realpath(__file__)), 'cork.exe'),
    'openscad': op.join(op.dirname(op.realpath(__file__)), 'openscad.exe'),
    'meshlab':  'C:\\Program Files\\VCG\\MeshLab\\meshlabserver.exe',
    'freecadp': 'C:\\Program Files\\FreeCAD 0.14\\bin\\python.exe'
  }
else:
  raise Exception('this script expects to be run either in Windows or in *NIX!!!')

"""If the arguments are strings from the user, execute the doDifference()
method in a safe way, checking everything and degrading gracefully"""
def safeDoDifference(strargs):
  arguments   = sanitizeStrArguments(*strargs)
  if not arguments.ok:
    return arguments
  try:
    ret       = doDifference(*(arguments.val))
  except:
    return RetVal(False, 'Unexpected exception: '+traceback.format_exc(), -1, 1)
  return ret  

"""make sure that all parameters are OK and consistent. Third element of
return tuples (False, msgstr, idx) is the index (in the list of arguments)
of the argument which caused the error. If successful, returns a list of
arguments which can be used to call doDifference.
ATTENTION: useXY and useZ are booleans, NOT STRINGS"""
def sanitizeStrArguments(filePC, fileSTL, fileResult, useXY, useZ, xmin, xmax, ymin, ymax, zmin, zmax, zsub):
  if not op.isfile(filePC):
    return RetVal(False, 'Error: point cloud input file does not exist: '+filePC, 0, 2)
  if not op.isfile(fileSTL):
    return RetVal(False, 'Error: STL input file does not exist: '+fileSTL, 1, 3)
  a,ext     = op.splitext(fileResult)
  dr        = op.dirname(fileResult)
  if ext.lower()!=".stl":
    return RetVal(False, 'Error: output file does not have STL extension: '+fileResult, 2, 4)
    return
  if dr!='' and not op.isdir(dr):
    return RetVal(False, 'Error: output file is not in a valid directory: '+fileResult, 2, 5)
  filePC     = str(op.abspath(filePC))
  fileSTL    = str(op.abspath(fileSTL))
  fileResult = str(op.abspath(fileResult))
  if useXY and not useZ:
    return RetVal(False, 'Error: if XY axes are enabled, Z axis must be also enabled', 3, 6)
  useCube = useXY
  limits  = [[xmin, xmax], [ymin, ymax], [zmin, zmax]]
  axes    = 'XYZ'
  lims    = ['min', 'max']
  uses    = [useXY, useXY, useZ]
  baseidx = 5
  idx     = baseidx
  for a in xrange(len(limits)):
    if uses[a]:
      for b in xrange(len(limits[a])):
        val = limits[a][b].strip()
        if val=='':
          return RetVal(False, 'Error: empty field for %c%s' % (axes[a], lims[b]), idx, 40+idx-baseidx)
        try:
          limits[a][b] = float(val)
        except:
          return RetVal(False, 'Error: invalid value for %c%s: %s' % (axes[a], lims[b], val), idx, 50+idx-baseidx)
        idx += 1
    else:
      limits[a] = []
  try:
    zsub = float(zsub)
  except:
    return RetVal(False, 'Error: invalid value for zsub: '+str(zsub), 11, 7)
  return RetVal(True, [filePC, fileSTL, fileResult, useCube, limits, zsub])
  
"""make sure that all limits are sane"""
def checklimits(useCube, limits, zsub):
  if zsub<=0:
    return RetVal(False, 'The depth parameter zsub must be higher than 0', 11, 8)
  if len(limits)!=3:
    return RetVal(False, 'Incorrect limits specification', -1, 9)
  lens = n.array([len(x) for x in limits])
  if useCube:
    if not (lens==2).all():
      return RetVal(False, 'all limits must be correctly populated', -1, 10)
    first = 0
  elif lens[2]==2:
    first = 2
  elif (lens==0).all():
    return RetVal(True)
  else:
    return RetVal(False, 'Incorrect limits specification', -1, 11)
  if useCube:
    first = 0
    idx   = 5
  else:
    first = 2
    idx   = 9
  baseidx = 5
  first   = 0 if useCube else 2
  names   = 'XYZ'
  lms     = ['min', 'max']
  submsg  = ['', '', ' in this configuration']
  #third element of return tuples (False, msgstr, idx) is the index (in the 
  #list of arguments) of the argument which caused the error
  for i in xrange(first,3):
    if limits[i][0]>=limits[i][1]:
      return RetVal(False, 'invalid condition: %cmin must be  lower than %cmax: %s, %s' % (names[i], names[i], str(limits[i][0]), str(limits[i][1])), idx, 60+idx-baseidx)
    for ii in xrange(2):
      if n.isnan(limits[i][ii]):
        return RetVal(False, 'invalid condition: %c%s cannot be nan' % (names[i], lms[ii]), idx, 70+idx-baseidx)
      if useCube and n.isinf(limits[i][ii]):
        return RetVal(False, '%c%s cannot be infinite%s' % (names[i], lms[ii], submsg[i]), idx, 80+idx-baseidx)
      idx += 1
  return RetVal(True)
  
#intermediate and temporary files, with small explanantion snippets
specialFiles = {
  'pc':   ('pc.off',    'point cloud in intermediate OFF format'),
  'stl':  ('stl.off',   'STL input mesh in intermediate OFF format'),
  'cube': ('cube.off',  'prism representing limits in XYZ axes in intermediate OFF format'),
  'int':  ('int.off',   'intermediate file (before applying XYZ limits) in OFF format'),
  'out':  ('out.off',   'output mesh in intermediate OFF format'),
  'scad': ('open.scad', 'specification file for the OpenSCAD mesh engine (if used)')
  }

#quick hack to avoid registering this file entry if we are not using openscad engine
if meshmode!='openscad': 
  specialFiles.pop('scad', None)

"""Intersect a point cloud and a STL model within a given box. The logic of the
function is spaguetti because we need to assume that anything could go wrong,
so we have to double-check everything and provide meaningful error messages"""
def doDifference(filePC, fileSTL, fileResult, useCube, limits, zsub):
  #we may use meshlab, but freecad seems to produce (for whatever reason)
  #better results (specifically, the STL output file had some flipped normals
  #with meshlab, while it didn't with freecad)
  mode = 'freecad'
  #mode = 'meshlab'
  #sanity check
  ret  = checklimits(useCube, limits, zsub)
  if not ret.ok: return ret
  #read point cloud
  try:
    pc = n.loadtxt(filePC, dtype=float, delimiter=';')
  except:
    return RetVal(False, 'Could not read point cloud file '+filePC, -1, 12)
  if pc.size==0:
    return RetVal(False, 'Incorrect or empty point cloud file '+filePC, -1, 13)
  if pc.shape[1]!=3:
    return RetVal(False, 'Point cloud must have 3 columns, but it has '+str(pc.shape[1]), 0, 14)
  #create mesh
  try:
    result   = createMeshFromPointCloud(pc, limits[2], zsub)
    pc=None
  except:
    return RetVal(False, 'Unexpected error while generating the mesh from the point cloud: '+traceback.format_exc(), 0, 15)
  if not result.ok:
    return result
  #compose absolute paths for intermediate and final files
  dirname    = op.dirname(fileSTL)
  fs         = {k: op.join(dirname,v[0]) for k, v in specialFiles.iteritems()}
  fileName, fileExtension = op.splitext(fileResult)#filePC)
  #fileResult = op.join(dirname, fileName+'.diff.stl')
  if fileExtension.lower()!='.stl': #heal fileResult if the extension is not correct
    fileResult = fileName+'.stl'
  if useCube:
    fileO    = fs['int']
  else:
    fileO    = fs['out']
  toRemove   = fs.values()
  #remove all possible intermediate files (and the final output STL file)
  #before starting, because we need to make sure that if a file is present,
  #it is because the conversion has been successful, not because it was
  #already there
  map(removefile, toRemove+[fileResult])
  if useCube:
    #create limiting cube and the related intermediate OFF file
    cube     = createCubicMesh(limits)
    createOffFromMesh(fs['cube'],  *cube)
    if not fileCheck(fs['cube'], toRemove): return RetVal(False, 'Failed before diff: could not create file '+fs['cube'], -1, 16)
  #create OFF files for CORK
  createOffFromMesh(fs['pc'], *result.val)
  result = None
  if not fileCheck(fs['pc'], toRemove):  return RetVal(False, 'Failed before diff: could not create file '+fs['pc'], -1, 17)
  ret = safeConvert(toolpaths, mode, fileSTL, fs['stl'], toRemove,
                    ('Failed before diff: could not convert the file %s to %s (%s may be invalid or be an empty mesh)' % (fileSTL, fs['stl'], fileSTL), -1, 18),
                    ('Failed before diff: unexpected error trying to convert the file %s to %s' % (fileSTL, fs['stl']), -1, 19))
  if not ret.ok: return ret
  #execute meshdiff engine
  ret   = callMeshEngine(toolpaths, toRemove, meshmode, 'diff',   fs, fs['pc'],  fs['stl'], fileO,      ('The meshdiff operation was not successful', -1, 20))
  if not ret.ok: return ret
  if useCube:
    #mesh engine another time: intersect with limiting cube
    ret = callMeshEngine(toolpaths, toRemove, meshmode, 'inters', fs, fs['int'], fs['cube'], fs['out'], ('The second meshdiff operation (with the prism) was not successful', -1, 21))
    if not ret.ok: return ret
  #convert OFF file to output STL file
  ret = safeConvert(toolpaths, mode, fs['out'], fileResult, toRemove,
                    ('Failed after diff: could not convert the file %s to %s (%s may be invalid or be an empty mesh)' % (fs['out'], fileResult, fs['out']), -1, 22),
                    ('Failed after diff: unexpected error trying to convert the file %s to %s' % (fs['out'], fileResult), -1, 23))
  if not ret.ok: return ret
  if not fileCheck(fileResult, toRemove): return RetVal(False, 'No errors were detected, but the output file was not created: '+fileResult, -1, 24)
  #if successful, unconditionally remove files
  map(removefile, toRemove)
  return RetVal(True, 'output file has been written: '+fileResult, -1, 0)

"""helper to execute the mesh engine controlling for possible errors at every step"""
def callMeshEngine(toolpaths, toRemove, mode, operation, fs, in1, in2, out, msg):
  try:
    #we support two operations: difference and intersection
    if operation=='diff':
      dodiff = True
    elif operation=='inters':
      dodiff = False
    else:
      cleanFiles(toRemove)
      return RetVal(False, 'Unexpected mesh engine operation: '+operation, -1, 25)
    #prepare command line for cork mesh engine
    if mode == 'cork':
      if not op.isfile(toolpaths['cork']):
        cleanFiles(toRemove)
        return RetVal(False, 'cork was selected as meshdiff engine, but the executable could not be found: '+toolpaths['cork'], -1, 26)
      operation = '-diff' if dodiff else '-isct'
      command = [toolpaths['cork'], operation, in1, in2, out]
    #prepare command line for openscad mesh engine
    elif mode == 'openscad':
      if (os.name=='nt') and not op.isfile(toolpaths['openscad']):
        cleanFiles(toRemove)
        return RetVal(False, 'openscad was selected as meshdiff engine, but the executable could not be found: '+toolpaths['openscad'], -1, 27)
      operation = 'difference' if dodiff else 'intersection'
      filestr = ('%s(){import("%s");import("%s");}' % (operation, str(in1).encode('string_escape'), str(in2).encode('string_escape')))
      with open(fs['scad'], 'w') as f:
        f.write(filestr)
      command = [toolpaths['openscad'], '-o', out, fs['scad']]
    #unrecognized engine
    else:
      cleanFiles(toRemove)
      return RetVal(False, 'Unrecognized mesh engine mode: '+mode, -1, 28)
    #execute engine
    sub.call(command)
    if not fileCheck(out, toRemove):
      return RetVal(False, *msg)
    return RetVal(True)
  except:
    cleanFiles(toRemove)
    return RetVal(False, 'Unexpected exception while executing %s mesh engine: %s' % (mode, traceback.format_exc()), -1, 29)

"""helper to execute the conversion engine (either freecad or meshlab) controlling for possible errors at every step"""
def safeConvert(toolpaths, mode, inp, outp, toRemove, msg1, msg2):
  if mode=='freecad':
    #command = '"%s" "%s" "%s" "%s"' % (toolpaths['freecadp'], freecadscript, inp, outp)
    command = [toolpaths['freecadp'], freecadscript, inp, outp]
  elif mode=='meshlab':
    #command = '"%s" -i "%s" -o "%s"' % (toolpaths['meshlab'], inp, outp)
    command = [toolpaths['meshlab'], '-i', inp, '-o', outp]
  else:
    Exception('Unrecognized mode for safeConvert: '+mode)
  try:
    #print command
    #os.system(command)
    sub.call(command)
    if not fileCheck(outp, toRemove):
      return RetVal(False, *msg1)
    return RetVal(True)
  except:
    if DEBUG: traceback.print_exc()
    cleanFiles(toRemove)
    return RetVal(False, *msg2)


"""logic to check if a file has been created, if it is not and we are not
debugging, remove all previous files"""
def fileCheck(path, toRemove):
  if op.isfile(path):
    return True
  else:
    cleanFiles(toRemove)
    return False

"""clean files in case of error"""
def cleanFiles(toRemove):
  if NOTDEBUG:
    map(removefile, toRemove)

"""remove files in a safe way"""
def removefile(path):
  try:
    #print 'trying to remove '+path
    if op.isfile(path):
      os.remove(path)
      #print '  DONE'
  except:
    if DEBUG: traceback.print_exc()


"""Creates a mesh from a point cloud, as a cylinder: top and base meshes
connected by a ribbon"""
def createMeshFromPointCloud(points, zlimits, zsub):#(d, zmax, zmin, zsub):
  #remove invalid points  
  if len(zlimits)==2:
    mask   = n.logical_and(points[:,2]<zlimits[1], points[:,2]>zlimits[0])
    if mask.all():
      usedPoints = points
    else:
      usedPoints = points[mask,:]
  else:
    usedPoints = points
  #create upper face
  try:
    #tessU = Delaunay(usedPoints[:,0:2], qhull_options='QJ') #This is to make sure that all points are used
    tessU = Delaunay(usedPoints[:,0:2])
  except:
    traceback.print_exc()
    return RetVal(False, 'Error trying to generate a mesh from the point cloud: Delaunay triangulation of the point cloud failed', -1, 30)
  tU = tessU.simplices
  
  #get border edges in border triangles
  i1, i2 = (tessU.neighbors==-1).nonzero() #indexes of vertexes not opossed to a triangle, they are not in the edge of the mesh, but the other two vertexes of the triangle are!
  i21 = (i2+1)%3  #these are the column indexes of vertexes in the edge of the mesh
  i22 = (i21+1)%3 #
  ps = n.column_stack((tU[i1,i21], tU[i1,i22])) #edges at the edge of the mesh
  #order the points in the edges (counterclockwise)
  ordered = n.empty(ps.shape[0], dtype=n.int32)
  ordered[0] = ps[0,0] #seed the sequence with the first edge
  ordered[1] = ps[0,1]
  ps[0,:] = -1
  io = 2
  while io<ordered.size:
    i1, i2 = (ps==ordered[io-1]).nonzero() #get the position of the last vertex in the ordered sequence
    if i1.size!=1: #each vertex should appear only twice in the list of edges
      return RetVal(False, "could not get ordered border for delaunay triangulation", -1, 31)
    ordered[io] = ps[i1, (i2+1)%2] #add the adjacent vertex to the ordered list
    ps[i1,:] = -1 #remove the edge from the list of edges
    io += 1
  #points in the base are those at the edge, but lowered by a certain amount  
  newpoints = usedPoints[ordered,:]
  newpoints[:,2] = usedPoints[:,2].min()-zsub
  #ordered list of vertexes at the edges of the upper mesh
  nidxU = ordered
  #same, list, but shifted
  nidxUp1 = n.concatenate((ordered[ordered.shape[0]-1:ordered.shape[0]], ordered[0:-1]))
  #ordered list of vertexes at the lower mesh
  nidxL = n.arange(usedPoints.shape[0], usedPoints.shape[0]+newpoints.shape[0])
  #same, list, but shifted the other way around
  nidxLm1 = n.concatenate((nidxL[1:nidxL.size], nidxL[0:1]))
  #triangles for the connecting ribbon
  Tmed1 = n.column_stack((nidxU, nidxUp1, nidxL))
  Tmed2 = n.column_stack((nidxLm1, nidxU, nidxL))
  #get base mesh
  try:
    #tessB = Delaunay(newpoints[:,0:2], qhull_options='QJ') #This is to make sure that all points are used
    tessB = Delaunay(newpoints[:,0:2])
  except:
    traceback.print_exc()
    return RetVal(False, 'Error trying to generate a mesh from the point cloud: Delaunay triangulation of the base failed', -1, 32)
  #reindex the triangles of the base mesh
  tB = nidxL[tessB.simplices]
  # this is to have all triangles of the base mesh to be counterclockwise
  tB = tB[:,[0,2,1]] 
  tA = n.concatenate((tU, Tmed1, Tmed2, tB))
  #create arrays with all points
  allPoints  = n.concatenate((usedPoints, newpoints))
  return RetVal(True, (allPoints, tA))
  #return RetVal(True, (allPoints, tA, (tU.copy(), Tmed1, Tmed2, tB)))
  


"""given a set of limits for each axis as [[xmin, xmax],[ymin, ymax],[zmin, zmax]],
generate a mesh representing a prism"""
def createCubicMesh(limits):
  xl,yl,zl=limits
  x1,x2=xl
  y1,y2=yl
  z1,z2=zl
  points = n.array([[x1,y1,z1],
                    [x2,y1,z1],
                    [x1,y2,z1],
                    [x2,y2,z1],
                    [x1,y1,z2],
                    [x2,y1,z2],
                    [x1,y2,z2],
                    [x2,y2,z2]], dtype=float)
  triangles = n.array([[0,1,2],
                       [1,3,2],
                       [0,6,4],
                       [0,2,6],
                       [1,5,3],
                       [3,5,7],
                       [1,0,5],
                       [0,4,5],
                       [2,3,6],
                       [3,7,6],
                       [4,6,7],
                       [4,7,5]])
  triangles = triangles[:,[0,2,1]] # flip normals
  return (points, triangles)

"""Given a mesh in the format (verts, triangs), create an OFF file"""
def createOffFromMesh(filename, verts, triangles):
  try:
    triangles = n.column_stack((n.full(triangles.shape[0], 3), triangles))
    with open(filename, 'w') as f:
      f.write("OFF\n")
      f.write("%s %s 0\n" % (str(verts.shape[0]), str(triangles.shape[0])))
      n.savetxt(f, verts,     fmt='%f')
      n.savetxt(f, triangles, fmt='%d')
  except:
    traceback.print_exc()

def dist(a, b):
  x = n.power(a-b, 2)
  #if len(x.shape)==1, x is a vector, so axis=0, otherwise it is a matrix, so sum along rows, so axis=1
  return n.sqrt(n.sum(x, axis=len(x.shape)!=1)) 

