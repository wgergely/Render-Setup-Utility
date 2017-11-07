import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds

class Events(object):
    def __init__(self, clientData=None):
        self.callbackIDs = []

        def _cb_addRemove(self, *args):
            print '_cb_connection'
            # https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2016/ENU/Maya-SDK/py-ref/class-open-maya-1-1-m-dag-message-html.html#pub-static-methods
            i = args[1]
            if args[2] is not None:
                if args[2].node() is not None:
                    s = args[2].node().apiTypeStr()
                    if i==0 or i==1 or i==2 or i==3:
                        if type(args[2]) is OpenMaya.MDagPath:
                            if s=='kMesh' or s=='kNurbsSurface':
                                print 'New object added/removed to/from scene'

        def _cb_connection(self, *args):
            print '_cb_connection'
            if type(args[2]) is OpenMaya.MPlug:
                if args[2].node().apiTypeStr()=='kShadingEngine':
                    print 'Node connected to shading engine.'
                if args[2].node().apiTypeStr()=='kRenderLayer':
                    print 'Node connected to render layer.'

        def _cb_scene(self, *args):
            print '_cb_scene'
            pass

        self.cb_addRemove = _cb_addRemove
        self.cb_connection = _cb_connection
        self.cb_scene = _cb_scene

    def addCallbacks(self):
        cb = OpenMaya.MDagMessage.addAllDagChangesCallback(self.cb_addRemove)
        self.callbackIDs.append(cb)
        cb = OpenMaya.MDGMessage.addConnectionCallback(self.cb_connection)
        self.callbackIDs.append(cb)
        return self.callbackIDs

    def removeCallbacks(self):
        OpenMaya.MMessage.removeCallbacks(self.callbackIDs)
