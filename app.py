#!/usr/bin/python

from __future__ import print_function

import sys#, os
import os.path as op
import traceback
import numpy as n
try:
  import meshdiff
except:
  print('The module meshdiff.py could not be loaded. It should be in the same directory as app.py: '+op.dirname(op.realpath(__file__)))
  traceback.print_exc()
  sys.exit(-1)

"""Main code path for using command line arguments"""
def mainCmdLineApp(argv):
  ret = None
  try:
    if not len(argv) in [4, 6, 10]:
      print('Incorrect number of arguments! Usage:')
      usage(argv)
      return
    usez      = len(argv)>=6
    usexy     = len(argv)==10
    strargs = argv[1:4]+[usexy, usez]
    if   len(argv)==4:  #no limits
      strargs = strargs+(['']*6)
    elif len(argv)==6:  #only zmin, zmax
      strargs = strargs+(['']*4)+argv[4:6]
    elif len(argv)==10: #all limits
      strargs = strargs+argv[4:10]
    strargs.append('0.1') #zsub
    ret = meshdiff.safeDoDifference(strargs)
    if ret.val:
      print(ret.val)
  except:
    print('Unexpected exception!!!')
    traceback.print_exc()
  if ret and (ret.errcode!=None):
    sys.exit(ret.errcode)
  sys.exit(-1)

"""Main code path for taking arguments from the user with a GUI"""
def mainGUIApp():
  try:
    import gui
  except:
    print('The module gui.py could not be loaded. It should be in the same directory as app.py: '+op.dirname(op.realpath(__file__)))
    traceback.print_exc()
    sys.exit(-1)
  gui.main()


"""command line help"""
def usage(argv):
  print('%s has four modes of operation, depending on the command line arguments:' % (argv[0]))
  print('')
  print('   %s' % (argv[0]))
  print('     with no arguments, this help text is displayed')
  print('')
  print('   %s -gui' % (argv[0]))
  print('     with one argument -gui, arguments are collected using a')
  print('     GUI interface (requires wxPython to be installed)')
  print('')
  print('   %s pcin stlin stlout [[Xmin Xmax Ymin Ymax] Zmin Zmax]' % (argv[0]))
  print('     with more than one argument, these are used to do the computations:')
  print('       -pcin:   input  point cloud file')
  print('       -stlin:  input  STL file')
  print('       -stlout: output STL file. ATTENTION: if this file already exists,')
  print('                it will be removed even if the process fails')
  print('          IF ANY FILE PATH CONTAINS SPACES OR NON-ALPHANUMERIC CHARACTERS,')
  print('          PUT IT INSIDE QUOTATION MARKS. EXAMPLE: "my file.txt"')
  print('       -Zmin Zmax: optional arguments representing limits to the ouput STL')
  print('                   in the Z axis (points outside the limits are culled)')
  print('       -[Xmin Xmax Ymin Ymax]: optional arguments representing limits')
  print('                               to the output STL in the XY plane')
  print('                               (points outside the limits are NOT culled)')
  print('')
  print('ATTENTION: In the directory of the output STL file, several files')
  print('           names are reserved. They are removed before starting the')
  print('           process. Please make sure you are not using these file names:')
  print('')
  #get list of file names and explanations
  fst = meshdiff.specialFiles.values()
  #get format for file names (to present the explanations in a tidy way)
  frmt = str(-(1+n.array([len(v[0]) for v in fst]).max()))
  strformat = '  %'+frmt+'s %s'
  for fn, exp in fst:
    print(strformat % (fn+':', exp))

"""main function"""
def main(argv):
  if len(argv)<2:
    usage(argv)
  elif argv[1].lower() in ['-gui', '-g']:
    mainGUIApp()
  else:
    mainCmdLineApp(argv)

if __name__=='__main__':
  main(sys.argv)