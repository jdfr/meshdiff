#!/usr/bin/python
import itertools as it
import os
import os.path as op
import traceback
import sys
try:
  import meshdiff
except:
  print('The module meshdiff.py could not be loaded. It should be in the same directory as gui.py: '+op.dirname(op.realpath(__file__)))
  traceback.print_exc()
  sys.exit(-1)
try:
  import wx
  import wx.lib.dialogs as wxd
except:
  print('The GUI could not be loaded. Is wxPython installed? The error is shown below: ')
  traceback.print_exc()
  sys.exit(-1)

errcode = -1

"""Pack elements of a list into a list of tuples, each one of length n"""
def group(lst, n):
  return it.izip(*[it.islice(lst, i, None, n) for i in range(n)])

class MeshDiffGUI(wx.Frame):
  
    def __init__(self, parent, title, siz):
        super(MeshDiffGUI, self).__init__(parent, title=title, 
            size=siz)
        
        self.InitUI(title)
        self.Centre()
        self.Show()
        self.SetMinSize(siz)
        
    def InitUI(self, title):
    
        parent = wx.Panel(self)
        #parent = self
        parent.SetBackgroundColour('#4f5049')
        
        #grid of widgets to input file names        
        fgsA = wx.FlexGridSizer(3, 3, 10, 10) 

        #ordered for intuitive tab navigation between controls
        lpc     = wx.StaticText(parent, style=wx.ALIGN_RIGHT, label="Point cloud file: ")
        tpc     = wx.TextCtrl(  parent)
        bpc     = wx.Button(    parent, label='Select File...')
        lstlin  = wx.StaticText(parent, style=wx.ALIGN_RIGHT, label="input STL file: ")
        tstlin  = wx.TextCtrl(  parent)
        bstlin  = wx.Button(    parent, label='Select File...')
        lstlout = wx.StaticText(parent, style=wx.ALIGN_RIGHT, label="output STL file: ")
        tstlout = wx.TextCtrl(  parent)
        bstlout = wx.Button(    parent, label='Select File...')
        
        fgsA.AddMany([lpc,     (tpc,     1, wx.EXPAND), bpc,
                      lstlin,  (tstlin,  1, wx.EXPAND), bstlin,
                      lstlout, (tstlout, 1, wx.EXPAND), bstlout])
        fgsA.AddGrowableCol(1, 1)

        #grid of widgets to input limits and misc stuff, and main buttons
        fgsB = wx.FlexGridSizer(3, 6, 10, 10)
        
        cexit = wx.CheckBox(parent, label='Close GUI if successful')
        cxy   = wx.CheckBox(parent, label='Use limits in XY axes')
        cz    = wx.CheckBox(parent, label='Use limits in Z axis')
        
        #labels and textcontrols for xmin,xmax,ymin,ymax
        lablims  = [wx.StaticText(parent, style=wx.ALIGN_RIGHT, label=ax+lim)
                    for ax in 'XYZ' for lim in ['min', 'max']]
        textlims = [wx.TextCtrl(parent) for x in lablims]
        
        #this is just in case the conf file is missing        
        for t in textlims:
          #as cz and cxy are initially unchecked, all textlims have to be initially disabled
          t.Enable(False)
        cexit.SetValue(True) #cexit has to be initially checked
        
        bcomp = wx.Button(parent, label='Compute')
        bexit = wx.Button(parent, label='Close')
        #do not put help button, but we need a placeholder for the FlexGridSizer
        bhelp = wx.StaticText(parent, label='') 
        #bhelp = wx.Button(parent, label='Help')
        
        #code to add all previously defined controls into the frexgridsizer
        cspecs = [(cexit, 0, wx.ALIGN_CENTER | wx.ALL, 0),
                  (cxy,   0, wx.ALIGN_LEFT   | wx.ALL, 0),
                  (cz,    0, wx.ALIGN_LEFT   | wx.ALL, 0)]
        lspecs = list(it.chain(*[[(x, 0, wx.ALL, 0), (y, 1, wx.EXPAND)]
                                         for x,y in zip(lablims, textlims)]))
        bspecs = [(x, 0, wx.ALIGN_CENTER | wx.ALL, 0) for x in [bcomp, bexit, bhelp]]
        #put the controls inside the flexgrdisizer in the right order
        specs = it.chain(*[(a,b[0],b[1],b[2],b[3],c)
                                for a,b,c in zip(cspecs, group(lspecs, 4), bspecs)])
        fgsB.AddMany(specs)
        fgsB.AddGrowableCol(2, 1)
        fgsB.AddGrowableCol(4, 1)
        
        bs4 = wx.BoxSizer(wx.VERTICAL)
        bs4.AddMany([(x, 1, wx.EXPAND | wx.ALIGN_TOP | wx.ALL, 10) for x in [fgsA, fgsB]])
        
        parent.SetSizer(bs4)
        
        self.SetName(title)
        
        #read values from the file and set the GUI accordingly
        values = readDefaultValues()
        controls = [tpc, tstlin, tstlout, cexit, cxy, cz]+textlims
        for i in xrange(len(values)):
          name = controls[i].GetClassName()
          if   name=='wxCheckBox':
            val = values[i].lower() in ("yes", "true", "t", "1")
            controls[i].SetValue(val)
          elif name=='wxTextCtrl':
            controls[i].SetValue(values[i])
          else:
            print 'Unexpected control type %s for value %s'%(name, values[i])
        #make sure that the checks are consistent
        if cxy.GetValue() and not cz.GetValue():
          cxy.SetValue(False)
        #set enable/disable state for textlims according to the checks
        flags = [cxy.GetValue(), cxy.GetValue(), cz.GetValue()]
        for tup, flag in zip(group(textlims, 2), flags):
          for lim in tup:
            lim.Enable(flag)
          
        
        #EVENT HANDLERS
        if os.name=='posix':
          txtext = '*.TXT;*.txt'
          stlext = '*.STL;*.stl'
        else:
          txtext = '*.txt'
          stlext = '*.stl'

        #close event (window and button)
        self.Bind(wx.EVT_CLOSE, closureClose(self, controls))        
        bexit.Bind(wx.EVT_BUTTON, closureClose(self, controls))
        #events for open/save file buttons          
        bpc.Bind(    wx.EVT_BUTTON, closureFileDialog(tpc,     'select point cloud file name: ',  txtext, wx.FD_OPEN))
        bstlin.Bind( wx.EVT_BUTTON, closureFileDialog(tstlin,  'select input STL file name: ',    stlext, wx.FD_OPEN))
        bstlout.Bind(wx.EVT_BUTTON, closureFileDialog(tstlout, 'select output STL file name: ',   stlext, wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT))
        #events for checkboxes
        cz.Bind( wx.EVT_CHECKBOX, closureCheck(cz,  [4, 5],       cxy, [0, 1, 2, 3], textlims, False))
        cxy.Bind(wx.EVT_CHECKBOX, closureCheck(cxy, [0, 1, 2, 3], cz,  [4, 5],       textlims, True))
        #compute event
        bcomp.Bind(wx.EVT_BUTTON, closureCompute(self, tpc, tstlin, tstlout, cz, cxy, cexit, textlims))
        #bcomp.Bind(wx.EVT_BUTTON, closureHelp)
        
"""event handler for closing the application. It has to write the parameters to
a file (in order to load them the next time), and close the window"""
def closureClose(frame, allcontrols):
  def handleEvent(event):
    values = [str(x.GetValue()) for x in allcontrols]
    writeDefaultValues(values)
    frame.Destroy()
  return handleEvent

"""event handler for the SELECT FILE buttons. It has to open a FileDialog
with the appropriate parameters and (if successful, fill the corresponding textcontrol)"""
def closureFileDialog(text, msge, typ, flag):
  def handleEvent(event):
    val = text.GetValue()
    if op.isfile(val):
      dr,nm = op.split(op.realpath(val))
    else:
      dr = os.getcwd()
      nm = ''
    dlg = wx.FileDialog(None, msge, dr, nm, typ, flag)
    if dlg.ShowModal() == wx.ID_OK:
      result = dlg.GetPath()
      text.SetValue(result)
    dlg.Destroy()
  return handleEvent

"""event handler for the useXY and useZ checkboxes. It has to enable/disable
the other checkbox, and enable/disable the associated textcontrols, all
accordingly to the semantics of useXY and useZ"""
def closureCheck(c1, rang1, c2, rang2, textlims, triggerval):
  def handleEvent(event):
    val = c1.GetValue()
    for i in rang1:
      textlims[i].Enable(val)
    if val==triggerval:
      c2.SetValue(val)
      for i in rang2:
        textlims[i].Enable(val)
  return handleEvent

"""event handler for the COMPUTE button: call meshdiff.safeDoDifference,
display resulting messages, and if successful and requested, close GUI"""
def closureCompute(frame, tpc, tstlin, tstlout, cz, cxy, cexit, textlims):
  def handleEvent(event):
    controls    = [tpc, tstlin, tstlout, cxy, cz]+textlims
    strargs     = [x.GetValue() for x in controls]
    strargs.append('0.1') #zsub
    ret = meshdiff.safeDoDifference(strargs)
    if ret.errcode!=None:
      global errcode
      errcode = ret.errcode
    if ret.ok:
      if cexit.GetValue():
        frame.Close()
        return
    if ret.val:
      msgbox(ret.val)
    if (ret.argnum>=0) and (ret.argnum<len(controls)):
      controls[ret.argnum].SetFocus()
  return handleEvent

"""use a dialog box to notify the user of something. If the message has several
lines (possibly because of containing a exception), the dialog allows to select
the text"""
def msgbox(message):
  if '\n' in message:
    wxd.scrolledMessageDialog(None, message, '')#, pos, size)
  else:
    dlg = wx.MessageDialog(None, message, '', wx.OK)
    #dlg = ScrolledMessageDialog(None, message, '', (20,20), None, wx.OK)
    dlg.ShowModal()
    dlg.Destroy()

"""hard-coded location of the file with the default values for the dialog boxes
(in order to present the user with the previous choices)"""
def valuesFileName():
  return op.join(op.dirname(op.realpath(__file__)), 'guivalues.conf')

"""read from file the default values, taking care not to trust that the values are valid"""
def readDefaultValues():
  values = []
  fn = valuesFileName()
  if op.isfile(fn):
    with open(fn, 'r') as f:
      values = f.read().splitlines()
  return values

"""write default values to file"""
def writeDefaultValues(values):
  fn = valuesFileName()
  with open(fn, 'w') as f:
    for v in values:
      f.write(str(v)+'\n')

"""main GUI loop"""
def main():
  try:
    app = wx.App()
    MeshDiffGUI(None, 'PC/MESH diff tool', (800, 300))
    app.MainLoop()
  except:
    print('Unexpected exception!!!')
    traceback.print_exc()
  sys.exit(errcode)


if __name__ == '__main__':
  main()