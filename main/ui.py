from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.OpenMayaUI as OpenMayaUI
import maya.api.OpenMaya as OpenMaya
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
from PySide2.QtCore import QProcess
import shiboken2

import re
import os
import os.path as path
import base64
import tempfile

import maya.cmds as cmds

import RenderSetupUtility.main.utility as utility
import RenderSetupUtility.main.shaderUtility as shaderUtility
import RenderSetupUtility.main.renderOutput as renderOutput
import RenderSetupUtility.main.utilities as util

import RenderSetupUtility.ac.autoConnect as autoConnect
import RenderSetupUtility.ac.templates as templates
import RenderSetupUtility.ac.psCommand as psCommand
import RenderSetupUtility.ac.aeCommand as aeCommand

# try:
#
# except:
#     raise RuntimeError('Unable to import MtoA python libraries. Make sure the Arnold plugin is loaded.')

"""
Main package item for ui and functionality creation.
Some of the defined functions need organising, eg. the autoConnect comp creator needs moving 'ac' submodules.

TODO:

There's lots to fix and change.

Add custom shader overrides:
"""

WINDOW_WIDTH = 370
WINDOW_HEIGHT = 350
WINDOW_BACKGROUND = (0.22, 0.22, 0.22)
FRAME_BACKGROUND = (0.245, 0.245, 0.245)
FRAME_MARGIN = (6,6)
SCROLLBAR_THICKNESS = 21
ACTIVEITEM_PREFIX = ' '
COLLECTION_SUFFIX = '_collection'
MIN_NUMBER_OF_ROWS = 2
MAX_NUMBER_OF_ROWS = 15

windowID            = 'RenderSetupUtilityWindow'
windowTitle         = 'Render Setup Utility'
windowNewLayerID    = 'RenderSetupUtilityNewLayerWin'
windowNewLayerTitle = 'Add New Render Layer'
windowRenameID      = 'RenderSetupUtilityRenameWin'
windowRenameTitle   = 'Rename Selected'
windowNewShaderID   = 'RenderSetupUtilityNewShaderWin'
windowNewShaderTitle= 'Assign Shader'

# Variable to store current list selection
global currentSelection
global propertyOverridesMode
global shaderOverrideMode
global selectedShaderOverride
global overrideShader
global cmd
global rsUtility
global rsRenderOutput
global rsShaderUtility
global window
global windowStyle

global DagObjectCreatedID
global NameChangedID
global SceneOpenedID
global SceneImportedID
global SceneSegmentChangedID

# Callbacks
def _DagObjectCreatedCB(clientData):
    def update():
        clientData.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)
def _NameChangedCB(clientData):
    def update():
        clientData.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)
def _SceneOpenedCB(clientData):
    def update():
        clientData.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)
    cmds.evalDeferred(update)
def _SceneImportedCB(clientData):
    def update():
        clientData.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)
    cmds.evalDeferred(update)
def _SceneSegmentChangedCB(clientData):
    def update():
        clientData.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)

def _removeCallbacks():
    OpenMaya.MEventMessage.removeCallback(DagObjectCreatedID)
    OpenMaya.MEventMessage.removeCallback(NameChangedID)
    OpenMaya.MEventMessage.removeCallback(SceneOpenedID)
    OpenMaya.MEventMessage.removeCallback(SceneImportedID)
    OpenMaya.MEventMessage.removeCallback(SceneSegmentChangedID)


currentSelection = None
propertyOverridesMode = False
shaderOverrideMode = False
selectedShaderOverride = None
overrideShader = None
cmd = {}
rsRenderOutput = renderOutput.RenderOutput()

# Helper functions
def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass
def resetOptionMenu(inName, inValue, rl=True):
    for item in cmds.optionMenu(inName, q = True, ill = True) or []:
        cmds.deleteUI(item)
    # Add default render layer to menu
    if rl:
        cmds.menuItem(rsUtility.defaultName, label = rsUtility.defaultName, p = inName, enable = True)
    for item in inValue:
        try:
            cmds.menuItem(item, label=item, p=inName)
        except:
            raise RuntimeError('Problem adding menu item.')
def selectOptionMenuItem(inMenuName, inName, rl=True):
    for index, item in enumerate(cmds.optionMenu(inMenuName, q=True, itemListShort=True)):
        okString = re.sub('[^0-9a-zA-Z:]', '_', inName).lstrip('1234567890').lstrip('_')
        if item == okString:
            cmds.optionMenu(inMenuName, e = True, select = index+1)
def _setTextScrollListVisibleItemNumber():
    QItem = window.findChild(QtWidgets.QWidget, 'rsShaderScrollList')
    fullPath = _getFullPath(QItem)
    allItems = cmds.textScrollList(fullPath, query=True, allItems=True)

    if allItems:
        if MIN_NUMBER_OF_ROWS < len(allItems) < MAX_NUMBER_OF_ROWS:
            cmds.textScrollList('rsShaderScrollList', edit=True, enable=True, numberOfRows=len(allItems))
            cmds.textField('rsFilterShaderList', edit=True, enable=True)
            return
        if len(allItems) >= MAX_NUMBER_OF_ROWS:
            cmds.textScrollList('rsShaderScrollList', edit=True, enable=True, numberOfRows=MAX_NUMBER_OF_ROWS)
            cmds.textField('rsFilterShaderList', edit=True, enable=True)
            return
        if len(allItems) <= MIN_NUMBER_OF_ROWS:
            cmds.textScrollList('rsShaderScrollList', edit=True, enable=True, numberOfRows=MIN_NUMBER_OF_ROWS)
            cmds.textField('rsFilterShaderList', edit=True, enable=True)
            return
    else:
        QItem = window.findChild(QtWidgets.QWidget, 'rsShaderScrollList')
        fullPath = _getFullPath(QItem)
        cmds.textScrollList(fullPath, edit=True, enable=True, numberOfRows=MIN_NUMBER_OF_ROWS)

        QItem = window.findChild(QtWidgets.QWidget, 'rsFilterShaderList')
        fullPath = _getFullPath(QItem)
        cmds.textField(fullPath, edit=True, enable=True)
        return
def _outputTemplate():
    # Output templates
    listItem = []
    menuName = 'rsuWindow_optionMenu05'
    for item in renderOutput.OUTPUT_TEMPLATES:
        listItem.append(item)
    resetOptionMenu(menuName, listItem, rl=False)
    imageFilePrefix = cmds.getAttr('%s.imageFilePrefix' % renderOutput.DEFAULTS_NODE)
    current = [t for t in renderOutput.OUTPUT_TEMPLATES if imageFilePrefix == t]
    if current:
        selectOptionMenuItem(menuName, current[0])
        rsRenderOutput.currentTemplate = current[0]

        cmds.button('rsuWindow_button14', edit=True, label='')

    # Versions
    lyr = rsUtility.activeLayer.name()
    listItem = []
    menuName = 'rsuWindow_optionMenu04'
    if cmds.optionMenu('rsuWindow_optionMenu05', query=True, value=True) == renderOutput.OUTPUT_TEMPLATES[0]:
        cmds.optionMenu('rsuWindow_optionMenu04', edit=True, enable=False)
        cmds.button('rsuWindow_button12', edit=True, enable=False)
    else:
        cmds.optionMenu('rsuWindow_optionMenu04', edit=True, enable=True)
        cmds.button('rsuWindow_button12', edit=True, enable=True)
        versions = rsRenderOutput.getVersions(lyr)
        if versions:
            resetOptionMenu(menuName, versions, rl=False)
            selectOptionMenuItem(menuName, versions[-1])
        else:
            resetOptionMenu(menuName, ['v001'], rl=False)
    _updatePathText()
def _updatePathText():
    # path text
    lyr = rsUtility.activeLayer.name()
    cmds.button('rsuWindow_button14', edit=True, label='Output path not yet set')
    padding = cmds.getAttr('%s.extensionPadding  ' % renderOutput.DEFAULTS_NODE)
    path = rsRenderOutput.pathStr(lyr)
    if path:
        path = path + '_' + '1'.zfill(padding) + '.exr'
        cmds.button('rsuWindow_button14', edit=True, label=path)
def getProperyOverridesMode(shaderName):
    """
    Returns the current applied attributes or false.
    """

    appliedAttributes = []
    c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
    for index, item in enumerate(rsUtility.overrideAttributes):
        if c.overrides(item['long']) is not None:
            appliedAttributes.append(c.overrides(item['long']).attributeName())
        else:
            appliedAttributes.append('')
    # If any of the attributes present enable propertyOverridesMode.
    if [attr for attr in rsUtility.overrideAttributes if attr['long'] in appliedAttributes] != []:
        return appliedAttributes
    else:
        return False
def setPropertyOverridesMode():

    """
    Sets Set mode and the appropiate checkbox values based
    on the existing collection's applied overrides.
    """

    global propertyOverridesMode

    sel = getListSelection()
    propertyOverridesMode = False
    appliedAttributes = []

    def setFalse():
        propertyOverridesMode = False

        QItem = _getQItem('rsuWindow_text01', QtWidgets.QLabel)
        QItem.setStyleSheet('{color: rgb(200,200,200)}')
        QItem.setText('Arnold Property Overrides')

        for index, item in enumerate(rsUtility.overrideAttributes):
            cmds.checkBox('rsuWindow_checkbox' + str(int(index+2)).zfill(2), edit=True, enable=True)
            cmds.text('rsuWindow_text' + str(int(index+2)).zfill(2), edit=True, enable=True)

    if sel == []:
        setFalse()
        return False

    # Return false if any of the selected is inactive.
    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)

        if rsShaderUtility.isActive(s) is False:
            setFalse()
            propertyOverridesMode = False
            return False
        mode = getProperyOverridesMode(shaderName)
        if mode is False:
            setFalse()
            propertyOverridesMode = False
            QItem = _getQItem('rsuWindow_text01', QtWidgets.QLabel)
            QItem.setText('No property overrides to change')
            QItem.setStyleSheet('QLabel {\
                color: rgb(50,50,50);\
                font-weight: normal;\
            }')
            return False

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
        mode = getProperyOverridesMode(shaderName)

        if mode:
            propertyOverridesMode = True

            # Setting checkbox values and ui
            for index, attr in enumerate(mode):
                if attr:
                    cmds.checkBox('rsuWindow_checkbox' + str(int(index+2)).zfill(2), edit=True, value=c.getOverrideValue(attr), enable=True)
                    cmds.text('rsuWindow_text' + str(int(index+2)).zfill(2), edit=True, enable=True)
                else: # Disabling checkbox if attribute is missing
                    cmds.checkBox('rsuWindow_checkbox' + str(int(index+2)).zfill(2), edit=True, enable=False)
                    cmds.text('rsuWindow_text' + str(int(index+2)).zfill(2), edit=True, enable=False)

            # Set string
            QItem = _getQItem('rsuWindow_text01', QtWidgets.QLabel)
            if len(sel) == 1:
                QItem.setText('Change Override Values:')
            if len(sel) > 1:
                QItem.setText('Change Override Values (multiple selected):')
            QItem.setStyleSheet('QLabel {\
                color: rgb(200,200,200);\
                font-weight: bold;\
            }')

            return True
        else:
            propertyOverridesMode = False
            # cmds.checkBox('rsuWindow_checkbox' + str(int(index+2)).zfill(2), edit=True, enable=False)
            # cmds.text('rsuWindow_text' + str(int(index+2)).zfill(2), edit=True, enable=False)

            # Setting checkbox values and ui
            for index, attr in enumerate(rsUtility.overrideAttributes):
                cmds.checkBox('rsuWindow_checkbox' + str(int(index+2)).zfill(2), edit=True, enable=False)
                cmds.text('rsuWindow_text' + str(int(index+2)).zfill(2), edit=True, enable=False)

            # Set string
            QItem = _getQItem('rsuWindow_text01', QtWidgets.QLabel)
            cmds.text('rsuWindow_text01', edit=True, label='No property overrides in the collection.', enableBackground=False)
            QItem.setStyleSheet('QLabel {color: rgb(50,50,50)}')

            return False
        break

def _hasOverride(shaderName):

    c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
    if c.hasChildren():
        pass
    else:
        return False
    for child in c.getChildren():
        if child.typeName()=='collection' and '{0}{1}'.format(shaderName.replace(':', '_'), COLLECTION_SUFFIX) in child.name():
            for o in child.getOverrides():
                if o.typeName() == 'shaderOverride':
                    cnxs = cmds.listConnections(o.name())

                    overrideShader = [cnx for cnx in cnxs if '_collection' not in cnx and '_msg' not in cnx]
                    if overrideShader:
                        pass
                    else:
                        return False

                    shaderName = rsShaderUtility.stripSuffix(overrideShader[0])
                    overrideShader = overrideShader[0]
                    mode = [s for s in shaderUtility.SHADER_OVERRIDE_OPTIONS if s['suffix'] in overrideShader]
                    if mode:
                        return True
    return False
def getShaderOverrideMode(shaderName):
    """
        Get override mode from collection.
    """

    c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
    if c.hasChildren() is False:
        return False

    for child in c.getChildren():
        if child.typeName()=='collection' and '{0}{1}'.format(shaderName.replace(':', '_'), COLLECTION_SUFFIX) in child.name():
            for o in child.getOverrides():
                if o.typeName() == 'shaderOverride':
                    #Getting shader name via connections
                    cnxs = cmds.listConnections(o.name())

                    # Filter collections and 'msg'
                    arr = [cnx for cnx in cnxs if '_collection' not in cnx and '_msg' not in cnx]
                    if arr == []:
                        return False

                    for item in arr:
                        shaderName = rsShaderUtility.stripSuffix(item)
                        overrideShader = item

                    mode = rsShaderUtility.getMode(overrideShader)
                    if mode:
                        return mode
                    else:
                        return False
def setShaderOverrideMode(query=False):
    """
        Set's the UI according to the current shader override mode.
    """

    global shaderOverrideMode
    global selectedShaderOverride
    global overrideShader

    sel = getListSelection()
    QItem = _getQItem('rsuWindow_text11', QtWidgets.QLabel)
    shaderOverrideMode = False
    overrideShader = None

    if sel == []:
        # Mode is false
        shaderOverrideMode = False
        selectedShaderOverride = None
        overrideShader = None
        QItem.setStyleSheet('QLabel {color: rgb(200,200,200)}')
        QItem.setText('Shader Override')
        return False

    # Return false if any of the selected is inactive.
    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)

        if rsShaderUtility.isActive(s) is False:
            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            QItem.setStyleSheet('QLabel {color: rgb(200,200,200); font-weight: normal;}')
            QItem.setText('Shader Override')
            return False

        mode = getShaderOverrideMode(shaderName)
        if mode is None:
            # Doesn't have a shader override
            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            QItem.setStyleSheet('QLabel {color: rgb(50,50,50); font-weight: bold;}')
            QItem.setText('No shader override in the collection to change.')
            return False

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        mode = getShaderOverrideMode(shaderName)

        if mode:
            shaderOverrideMode = True
            selectedShaderOverride = mode['ui']
            selectOptionMenuItem('rsuWindow_optionMenu02', selectedShaderOverride)

            if len(sel) == 1:
                # QItem.setStyleSheet('QLabel {color: rgb(200,50,50); font-weight: bold;}')
                QItem.setText('Swap Shader')
            if len(sel) > 1:
                # QItem.setStyleSheet('QLabel {color: rgb(200,50,50); font-weight: bold;}')
                QItem.setText('Swap Shader (multiple selected)')
            return True
        if mode is False:
            # Doesn't have a shader override
            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            QItem.setStyleSheet('QLabel {color: rgb(50,50,50); font-weight: bold;}')
            QItem.setText('No shader override in the collection to change.')
            return False
        break

def getListSelection():
    sel = cmds.textScrollList('rsShaderScrollList', query=True, selectItem=True)
    if sel is None:
        return []
    else:
        return sel

def rsSelectLayer(arg):
    if arg == rsUtility.renderSetup.getDefaultRenderLayer().name():
        try:
            rsUtility.renderSetup.switchToLayer(rsUtility.renderSetup.getDefaultRenderLayer())
        except:
            raise RuntimeError('Couldn\'t switch to the default render layer.')
        window.updateUI(updateRenderSetup=True)
    else:
        rsUtility.switchLayer(arg)
        window.updateUI(updateRenderSetup=True)
        return arg
cmd['rsSelectLayer'] = rsSelectLayer

def _filterInvalidInput(name):
    data = cmds.textField(
        name,
        query=True,
        text=True
    )

    inp = re.sub('[^0-9]', '', data)
    if len(inp) == 0:
        return None

    data = cmds.textField(
        name,
        edit=True,
        text=inp
    )
    return int(inp)


def getInFrame():
    return cmds.playbackOptions(
        query=True,
        animationStartTime=True
)
def getOutFrame():
    return cmds.playbackOptions(
        query=True,
        animationEndTime=True
)
def setInFrame(*args):
    frame = _filterInvalidInput('%s_setInFrame' % (RenderSetupUtilityWindow.__name__))

    if frame is None:
        return

    frame = round(frame, 0)
    currentFrame = round(cmds.currentTime(query=True))

    cmds.playbackOptions(animationStartTime=int(frame))
    cmds.playbackOptions(minTime=int(frame))
    cmds.setAttr('defaultRenderGlobals.startFrame', frame)

    if currentFrame < frame:
        cmds.currentTime(frame, edit=True)
    else:
        cmds.currentTime(currentFrame, edit=True)
cmd['setInFrame'] = setInFrame

def setOutFrame(*args):
    frame = _filterInvalidInput('%s_setOutFrame' % (RenderSetupUtilityWindow.__name__))

    if frame is None:
        return

    frame = round(frame, 0)
    currentFrame = round(cmds.currentTime(query=True))

    cmds.playbackOptions(animationEndTime=int(frame))
    cmds.playbackOptions(maxTime=int(frame))
    cmds.setAttr('defaultRenderGlobals.endFrame', frame)

    if currentFrame > frame:
        cmds.currentTime(frame, edit=True)
    else:
        cmds.currentTime(currentFrame, edit=True)
cmd['setOutFrame'] = setOutFrame


def rsuWindow_optionMenu02(arg):
    """
    Shader overrides option menu.
    """

    global shaderOverrideMode
    global selectedShaderOverride

    sel = getListSelection()

    if shaderOverrideMode is False:
        return

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        if rsShaderUtility.isActive(s):
            c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
            if c.hasChildren():
                for child in c.getChildren():
                    if child.typeName()=='collection' and '{0}{1}'.format(shaderName.replace(':', '_'), COLLECTION_SUFFIX) in child.name():
                        for o in child.getOverrides():
                            if o.typeName() == 'shaderOverride':
                                newShader = rsShaderUtility.duplicateShader(shaderName, choice=arg, isOverride=True)
                                o.setSource(newShader+'.outColor')

                                overrideShader = newShader
                                selectedShaderOverride = arg
    selectedShaderOverride = arg
cmd['rsuWindow_optionMenu02'] = rsuWindow_optionMenu02

def rsuWindow_optionMenu03(arg):
    """
    Render Output Size Templates
    """
    r = renderOutput.RESOLUTION_NODE
    choice = [c for c in renderOutput.SIZE_TEMPLATE if arg == c['ui']][0]
    cmds.setAttr( '%s.width'%r, choice['width'])
    cmds.setAttr( '%s.height'%r, choice['height'])
    cmds.setAttr( '%s.deviceAspectRatio '%r, float((float(choice['width'])/float(choice['height']))) )
    cmds.setAttr( '%s.aspectLock  '%r, False )
    cmds.setAttr( '%s.pixelAspect   '%r, float(1) )

    c = 'camera'
    if cmds.objExists(c):
        currentAperture = cmds.getAttr('%s.cameraAperture'%c)[0]
        aspect = float(float(choice['width'])/float(choice['height']))
        cmds.setAttr( '%s.cameraAperture'%c, currentAperture[0],currentAperture[0]/aspect, type='double2')
        cmds.setAttr( '%s.lensSqueezeRatio'%c, float(1.0))
    print '# Output size changed to %s'%choice['ui']
cmd['rsuWindow_optionMenu03'] = rsuWindow_optionMenu03

def rsuWindow_optionMenu04(arg):
    rsRenderOutput.setVersion(arg)
cmd['rsuWindow_optionMenu04'] = rsuWindow_optionMenu04

def rsuWindow_optionMenu05(arg):
    version = cmds.optionMenu('rsuWindow_optionMenu04', query=True, value=True)
    rsRenderOutput.setTemplate(arg, version)
    rsRenderOutput.currentTemplate = arg
    _outputTemplate()
cmd['rsuWindow_optionMenu05'] = rsuWindow_optionMenu05

def rsuWindow_optionMenu06(arg):
    current = [t for t in renderOutput.TIME_TEMPLATE if arg == t['ui']]
    if current:
        cmds.currentUnit(time=current[0]['name'], updateAnimation=False)
        cmds.playbackOptions(edit=True, playbackSpeed=current[0]['fps'])
cmd['rsuWindow_optionMenu06'] = rsuWindow_optionMenu06

def rsShaderGroups(arg):
    text = cmds.textField('rsFilterShaderList', edit=True, text=arg)
    window.updateUI(updateRenderSetup=False)
cmd['rsShaderGroups'] = rsShaderGroups

def rsOpenRenderSetupWindow(arg):
    import maya.app.renderSetup.views.renderSetup as renderSetupUI
    renderSetupUI.createUI()
cmd['rsOpenRenderSetupWindow'] = rsOpenRenderSetupWindow

def rsAddNewLayer(item):
    """
    Window to add new layers.
    """

    WIDTH = WINDOW_WIDTH*(float(4)/5)
    OFFSET = WINDOW_WIDTH*(float(1)/5)
    HEIGHT = 75
    MARGIN = FRAME_MARGIN[0]

    if cmds.window(windowNewLayerID, exists = True):
        cmds.deleteUI(windowNewLayerID)

    cmds.window(
        windowNewLayerID,
        sizeable = False,
        title = windowNewLayerTitle,
        iconName = windowNewLayerTitle,
        width = WIDTH,
        height = HEIGHT
    )

    def rsuNewLayerWindow_button01(arg):
        text = cmds.textField('rsuNewLayerWindow_textField01', query = True, text = True)
        if len(text) > 0:
            rsUtility.layer(text)
        cmds.deleteUI(windowNewLayerID, window = True)
        window.updateUI(updateRenderSetup=True)
    def rsuNewLayerWindow_textField01(arg):
        if len(arg) == 0:
            cmds.button('rsuNewLayerWindow_button01', edit = True, enable = False)
        else:
            cmds.button('rsuNewLayerWindow_button01', edit = True, enable = True)

    cmds.columnLayout('rsuNewLayerWindow_columnLayout01',
        parent = windowNewLayerID,
        columnAlign = 'center',
        columnAttach = ('both', 10),
        columnWidth = WIDTH,
        rowSpacing = 1
    )
    addSeparator('rsuNewLayerWindow_sep01', height=MARGIN)
    addText('rsuNewLayerWindow_enterText', 'New layer name:', font='boldLabelFont')
    addSeparator('rsuNewLayerWindow_sep02', height=MARGIN)
    addTextField('rsuNewLayerWindow_textField01', '', rsuNewLayerWindow_textField01, rsuNewLayerWindow_textField01, rsuNewLayerWindow_textField01)
    cmds.columnLayout('rsuNewLayerWindow_columnLayout02', columnAlign='center', columnAttach=('both',0), columnWidth=WIDTH-MARGIN*2)
    addButton( 'rsuNewLayerWindow_button01', 'Create', command=rsuNewLayerWindow_button01, enable = False)
    addSeparator('rsuNewLayerWindow_sep03', height=MARGIN)
    cmds.showWindow( cmds.window(windowNewLayerID, q=True))

    # Match window position to parent
    QItem =_getQItem(windowNewLayerID, QtWidgets.QWidget)
    globalPos = window.mapToGlobal(window.pos())
    x = globalPos.x()+28
    y = globalPos.y()
    QItem.move(x, y)
cmd['rsAddNewLayer'] = rsAddNewLayer

def rsAddCollection(arg):
    """
    > Add collection based on the selected shader names to the selected render layer.

    Removes objects from any other collections in the layer
    and sets objects used by the shader as the sole selected objects.
    """

    global selectedShaderOverride
    global currentSelection

    DEFAULT_FILTER_TYPE = 2 #shape

    # Disable ui updates
    QItem = _getQItem(windowID, QtWidgets.QWidget)
    QItem.setUpdatesEnabled(False)

    # Change Override values from UI
    for index, item in enumerate(rsUtility.overrideAttributes):
        rsUtility.overrideAttributes[index]['default'] = cmds.checkBox('rsuWindow_checkbox' + str(2+index).zfill(2), query=True, value=True)

    sel = getListSelection()
    _currentSelection = []

    for s in sel:

        shaderName = rsShaderUtility.customStringToShaderName(s)
        _currentSelection.append(shaderName)

        rsUtility.activeLayer.collection(
            shaderName.replace(':', '_'),
            addOverrides = cmds.checkBox('rsArnoldPropertyOverridesCheckBox', query=True, value=True)
        )

        # Add used shapes to the active collection
        rsUtility.activeCollection.setSelection(
            rsShaderUtility.data[shaderName]['usedBy'],
            DEFAULT_FILTER_TYPE
        )

        #Remove objects from other collections:
        cl = rsUtility.activeLayer.getCollections()
        for c in cl:
            if c.name() != rsUtility.activeCollection.name():
                if c.typeName() == 'collection':
                    c.getSelector().staticSelection.remove(rsShaderUtility.data[shaderName]['usedBy'])

        # Shader override
        shaderOverrideCB = cmds.checkBox('rsuWindow_checkbox11', query=True, value=True)

        if shaderOverrideCB:
            choice = cmds.optionMenu('rsuWindow_optionMenu02', query=True, value=True)

            # Create the shader override shader
            overrideShader = rsShaderUtility.duplicateShader(shaderName, choice=choice, apply=shaderOverrideCB)

            o = rsUtility.addShaderOverride()
            o.setSource(overrideShader + '.outColor')

            selectedShaderOverride = choice

    currentSelection = _currentSelection
    QItem.setUpdatesEnabled(True)
    window.updateUI(updateRenderSetup=True)

cmd['rsAddCollection'] = rsAddCollection

def rsRemoveCollection(arg):
    """ < Remove colllections """
    # Disable ui updates
    QItem = _getQItem(windowID, QtWidgets.QWidget)
    QItem.setUpdatesEnabled(False)

    sel = getListSelection()
    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        rsUtility.activeLayer.removeCollection(shaderName.replace(':', '_'))


    QItem.setUpdatesEnabled(True)
    window.updateUI(updateRenderSetup=True)

cmd['rsRemoveCollection'] = rsRemoveCollection

def rsRenameShader(arg):
    """
    Rename
    """
    sel = getListSelection()
    if sel is None or sel is []:
        return None
    else:
        if len(sel) != 1:
            return None

    WIDTH = WINDOW_WIDTH*(float(4)/5)
    OFFSET = WINDOW_WIDTH*(float(1)/5)
    HEIGHT = 75
    MARGIN = 8

    if cmds.window(windowRenameID, exists = True):
        cmds.deleteUI(windowRenameID)

    cmds.window(
        windowRenameID,
        sizeable = False,
        title = windowRenameTitle,
        iconName = windowRenameTitle,
        width = WIDTH,
        height = HEIGHT
    )

    def rsuRenameWindow_button01(arg):
        global currentSelection
        global rsShaderUtility

        text = cmds.textField('rsuRenameWindow_textField01', query=True, text=True)
        sel = getListSelection()
        if len(text) > 0:
            shaderName = rsShaderUtility.customStringToShaderName(sel[0])
            items = cmds.ls(shaderName + '*', absoluteName=False, long=True)
            for item in items:
                if cmds.objExists(item):
                    cmds.rename(item, item.replace(shaderName, text))

        sel = getListSelection()
        shaderName = rsShaderUtility.customStringToShaderName(sel[0])
        _currentSelection = []
        currentSelection = _currentSelection.append(shaderName)

        rsShaderUtility = shaderUtility.ShaderUtility()
        window.updateUI()
        cmds.deleteUI(windowRenameID, window=True)

    def rsuRenameWindow_textField01(arg):
        try: # rsuRenameWindow_button01 does not exist the first time this is called
            if len(arg) == 0:
                cmds.button('rsuRenameWindow_button01', edit=True, enable=False)
            else:
                if arg in _matList():
                    cmds.button('rsuRenameWindow_button01', edit=True, enable=False, label='Name exists already')
                else:
                    cmds.button('rsuRenameWindow_button01', edit=True, enable=True, label='Rename')
        except:
            pass


    cmds.columnLayout('rsuRenameWindow_columnLayout01',
        columnAlign = 'center',
        columnAttach = ('both', 10),
        columnWidth = WIDTH,
        rowSpacing = 1
    )
    addSeparator('rsuRenameWindow_sep01', height=MARGIN)
    addText('rsuRenameWindow_enterText', 'Enter New Name:', font='boldLabelFont')
    addSeparator('rsuRenameWindow_sep02', height=MARGIN)

    addTextField('rsuRenameWindow_textField01', '', rsuRenameWindow_textField01, rsuRenameWindow_textField01, rsuRenameWindow_textField01)

    sel = getListSelection()
    shaderName = rsShaderUtility.customStringToShaderName(sel[0])
    text=cmds.textField('rsuRenameWindow_textField01', edit=True, text=shaderName)

    cmds.columnLayout('rsuRenameWindow_columnLayout02', columnAlign = 'center', columnAttach=('both',0), columnWidth = WIDTH-MARGIN*2)
    addButton( 'rsuRenameWindow_button01', 'Rename', command=rsuRenameWindow_button01, enable=False)
    addSeparator('rsuRenameWindow_sep03', height=MARGIN)
    cmds.showWindow( cmds.window(windowRenameID, q=True))

    QItem =_getQItem(windowRenameID, QtWidgets.QWidget)
    globalPos = window.mapToGlobal(window.pos())
    x = globalPos.x()+28
    y = globalPos.y()
    QItem.move(x, y)
cmd['rsRenameShader'] = rsRenameShader

def rsSelectShapes(arg):
    """
    Select shape transforms
    """

    parents = []
    sel = getListSelection()
    for s in sel:
        n = rsShaderUtility.customStringToShaderName(s)
        usedBy = rsShaderUtility.data[n]['usedBy']
        for u in usedBy:
            parent = cmds.listRelatives(u, allParents=True, path=True)[0]
            parents.append(parent)
    cmds.select(parents)
cmd['rsSelectShapes'] = rsSelectShapes

def rsRefreshUI(arg):
    """ Refresh button """
    window.updateUI()
cmd['rsRefreshUI'] = rsRefreshUI

def duplicateShader(arg):
    global rsShaderUtility

    l = []
    sel = getListSelection()
    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        duplicate = rsShaderUtility.duplicateShader(shaderName, isOverride=False)
        rsShaderUtility.copyShaderAttributes(shaderName, duplicate)
cmd['duplicateShader'] = duplicateShader

def editTexture(arg):
    """ AutoConnect - Edit Textures """

    # Check if ac found a valid Photoshop path:
    if autoConnect.AutoConnect.PHOTOSHOP_PATH is None:
        raise WindowsError('Sorry, couldn\'t find an Adobe Photoshop installation in the Windows Registry.')


    ac = autoConnect.AutoConnect()

    sel = getListSelection()
    if sel == []:
        print('# Edit Texture: No shader selected #')
        return

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        if [k for k in ac.DATA.keys() if shaderName == k] == []:
            print('# No texture file found to edit for the specified shader. #')
            raise RuntimeError('There doesn\'t seem to be an AutoConnect setup for the shader.')

        np = path.normpath(ac.DATA[shaderName]['psdPath'])
        print '# Edit Texture: Opening texture file for shader \'%s\': %s' % (shaderName, np)
        cmd = '"%s" "%s"' % (path.normpath(ac.PHOTOSHOP_PATH), np)
        process = QProcess()
        process.startDetached(cmd)

        break
cmd['editTexture'] = editTexture

def updateConnections(arg):
    """ AutoConnect - Update connections """

    sel = getListSelection()
    if sel == []:
        print '# Update Connections: No shader selected #'
        return

    ac = autoConnect.AutoConnect()

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        print '# Updating \'%s\' shader connections... #' % shaderName
        ac.doIt(shaderName)
cmd['updateConnections'] = updateConnections

def rsuWindow_button11(arg):
    pass
cmd['rsuWindow_button11'] = rsuWindow_button11

def rsuWindow_button12(arg):
    menuName = 'rsuWindow_optionMenu04'
    lyr = rsUtility.renderSetup.getVisibleRenderLayer().name()
    versions = rsRenderOutput.getVersions(lyr)
    if versions:
        search = re.search('[0-9]{3}', versions[-1])
        if search:
            newVersion = 'v%s' % str(int(search.group(0)) + 1).zfill(3)
            rsRenderOutput.addVersionDir(lyr, newVersion)
            _outputTemplate()
    _updatePathText()
cmd['rsuWindow_button12'] = rsuWindow_button12

def makeComp(arg):
    """
    AutoConnect - Make Comp

    Creates a temporary placeholder exr sequence for the current render layer.
    Also export and imports the camera called 'camera'.

    If the current render setup layer name contains 'layout' then the placeholder sequence
    will be substituted with a playblast of 'camera'.
    """

    pathControlSelection = cmds.optionMenu('rsuWindow_optionMenu05', query=True, value=True)
    if cmds.objExists('camera') is False:
        print('# Couldn\'t find \'camera\' #')
        raise RuntimeError('Couldn\'t find the camera. Make sure the main camera is called \'camera\'')

    si = autoConnect.SceneInfo()

    if si.isSceneSaved is False:
        print '# Scene has not been saved yet #'
        raise RuntimeError('_\n%s' % 'Scene hasn\'t been saved')

    DATA = {}

    BASE_PATH = None
    START_FRAME = si.startFrame
    END_FRAME = si.endFrame
    DURATION = si.duration
    currentTime = si.currentTime
    FRAME_RATE = si.frameRate
    LAYER_NAME = None
    VERSION = None
    EXTENSION = 'exr'
    IMAGE_PATH = None

    sn = cmds.file(query=True,sn=True, shortName=True)
    if sn:
        SCENE_NAME = sn.split('.')[0][:-4] # removes the versioning // Studio AKA specific setting.
    else:
        SCENE_NAME = 'untitled_maya_scene'


    currentWidth = si.currentWidth
    currentHeight = si.currentHeight
    OUTPUT_OPTION = [w for w in renderOutput.SIZE_TEMPLATE if currentWidth == w['width'] and currentHeight == w['height']]
    TEMPLATE = None
    IMAGE_PATHS = []
    FOOTAGE_NAMES = []
    MAYA_CAMERA = None


    # Check output templates
    if OUTPUT_OPTION == []:
        raise RuntimeError(
            'The current output size is not one of the defined templates. This is unsupported.\n\
            To continue, select one of the templated output formats.'
        )
    TEMPLATE = OUTPUT_OPTION[0]['suffix']

    if pathControlSelection == renderOutput.OUTPUT_TEMPLATES[0]:
        print ('# Output path not yet set #')
        raise RuntimeError(
            'Path template is not set. To continue, select one of the output path templates.'
        )

    LAYER_NAME = rsUtility.renderSetup.getVisibleRenderLayer().name()
    VERSION = cmds.optionMenu('rsuWindow_optionMenu04', query=True, value=True)


    # LOOP THROUGH AOVS
    for aov in rsRenderOutput._getAOVs():
        # Mark a spacial case when the layername contains 'layout'.
        # In this case, rather than writing a blank exr placeholder sequence,
        # we'll export a playblast of the 'camera' to the current ouput folder and ignore any active AOVs.
        #
        # The playblast is done via a custom modelPanel that inherits it's settings from the first modelPanel
        # currently using the 'camera'

        # Set base path
        if 'layout' in LAYER_NAME:
            BASE_PATH = rsRenderOutput.pathStr(LAYER_NAME, long=True)
        else:
            BASE_PATH = rsRenderOutput.pathStr(LAYER_NAME, long=True).replace('<AOV>', aov)

        if BASE_PATH is None:
            raise RuntimeError(
                'Couldn\'t get path from the render output path tokens.'
            )

        # Make folders
        k = BASE_PATH.rfind('\\')
        root = BASE_PATH[:k]

        if os.path.isdir(root) is False:
            os.makedirs(root)

        # Decode the exr template file
        decoded = base64.b64decode(templates.EXR_TEMPLATES[TEMPLATE])

        if 'layout' in LAYER_NAME:
            p = '%s.%s.%s' % (BASE_PATH, str(int(START_FRAME)).zfill(4), 'jpg')
            IMAGE_PATH = os.path.normpath(p)
        else:
            p = '%s_%s.%s' % (BASE_PATH, str(int(START_FRAME)).zfill(4), EXTENSION)
            IMAGE_PATH = os.path.normpath(p)

        confirm = 'Overwrite'

        if os.path.isfile(IMAGE_PATH) is True:
            confirm = cmds.confirmDialog(
                title='Warning',
                message='\
%s - %s: Render images already exists at the current location.\n\n\
If you choose \'Overwrite\', they will be replaced with a blank placeholder sequence.\n\
Otherwise click \'Import Existing\' to import the existing sequence (recommended).\n\n\
Image Path:\n%s\
' % (LAYER_NAME, aov, IMAGE_PATH),
                button=['Import Existing', 'Overwrite'],
                defaultButton='Import Existing',
                cancelButton='Import Existing',
                dismissString='Import Existing'
            )

        if confirm == 'Overwrite':
            if 'layout' in LAYER_NAME:
                p = '%s' % (BASE_PATH)
                IMAGE_PATH = os.path.normpath(p)

                multiSample = cmds.getAttr("hardwareRenderingGlobals.multiSampleEnable")
                ssao = cmds.getAttr("hardwareRenderingGlobals.ssaoEnable")

                window = autoConnect.captureWindow(int(currentWidth)*0.5, (int(currentHeight)*0.5)+30)

                # Tying to force Maya to retain this setting...
                cmds.setAttr('%s.imageFormat'%renderOutput.DEFAULTS_NODE, 8) # Set image format to jpg
                cmds.setAttr('perspShape.renderable', 0) # Make pers non-renderable
                cmds.setAttr('cameraShape.renderable', 1) # Make camera renderable, if exists.

                cmds.playblast(
                    # compression=compression,
                    format='image',
                    percent=int(100),
                    viewer=False,
                    startTime=int(START_FRAME),
                    endTime=int(END_FRAME),
                    showOrnaments=True,
                    forceOverwrite=True,
                    filename=str(IMAGE_PATH),
                    widthHeight=[int(currentWidth), int(currentHeight)],
                    rawFrameNumbers=True,
                    framePadding=int(4))

                cmds.setAttr("hardwareRenderingGlobals.multiSampleEnable", multiSample)
                cmds.setAttr("hardwareRenderingGlobals.ssaoEnable", ssao)

                window.close()

                p = '%s.%s.%s' % (BASE_PATH, str(int(START_FRAME)).zfill(4), 'jpg')
                IMAGE_PATH = os.path.normpath(p)
            else:
                for index, n in enumerate(DURATION):
                    p = '%s_%s.%s' % (BASE_PATH, str(n).zfill(4), EXTENSION)
                    IMAGE_PATH = os.path.normpath(p)
                    try:
                        imageFile = open(IMAGE_PATH, 'w')
                        imageFile.write(decoded)
                        imageFile.close()
                    except:
                        print '# Couldn\'t create temp image files.'

        IMAGE_PATH = os.path.normpath(p)
        IMAGE_PATHS.append(str(IMAGE_PATH))
        footageName = BASE_PATH[k+1:]
        FOOTAGE_NAMES.append('%s_%s' % (aov, str(footageName)))

        # Ignore AOVs
        if 'layout' in LAYER_NAME:
            break

    # House cleaning
    rsUtility.removeMissingSelections()

    # Export Camera from scene
    MAYA_CAMERA = autoConnect.exportCamera()
    if MAYA_CAMERA:
        pass
    else:
        raise RuntimeError('Couldn\'t export maya camera.')
    #############################################################
    # Time to call Ater Effects

    if IMAGE_PATHS:
        pass
    else:
        raise RuntimeError('No image path could be found to export.')

    ac = autoConnect.AutoConnect()
    aePath = ac.AFTER_EFFECTS_PATH
    if aePath:
        pass
    else:
        raise RuntimeError('Couldn\'t find After Effects.')

    tempfile.gettempdir()
    scriptPath = os.path.normpath(os.path.join(tempfile.gettempdir(), 'aeCommand.jsx'))

    ##############################################
    # Script file

    script = aeCommand.script
    AE_SCRIPT = script.replace(
        '<Name>', str(SCENE_NAME)).replace(
        '<Width>', str(currentWidth)).replace(
        '<Height>', str(currentHeight)).replace(
        '<Pixel_Aspect>', str(1)).replace(
        '<Duration>', str(float(len(DURATION))/float(FRAME_RATE))).replace(
        '<Frame_Rate>', str(float(FRAME_RATE))).replace(
        '<Image_Paths>', str(IMAGE_PATHS)).replace(
        '<Footage_Names>', str(FOOTAGE_NAMES)).replace(
        '<Maya_Camera>', MAYA_CAMERA.replace('\\', '\\\\')
        )
    ##############################################

    AE_SCRIPT_FILE = open(scriptPath,'w')
    AE_SCRIPT_FILE.write(str(AE_SCRIPT))
    AE_SCRIPT_FILE.close()

    try:
        cmd = '"%s" -r "%s"' % (ac.AFTER_EFFECTS_PATH, scriptPath)
        process = QProcess()
        process.startDetached(cmd)
    except KeyError:
        print("# There doesn't seem to be an AutoConnect setup for that shader.")
cmd['makeComp'] = makeComp

def rsuWindow_button14(arg):
    IMAGES_ROOT = 'images'

    val = cmds.button('rsuWindow_button14', query=True, label=True)
    if val == 'Output path not yet set':
        return
    else:
        workspace = cmds.workspace(query=True, rootDirectory=True)
        if workspace:
            # workspace = sceneName.rsplit('\\', 1)[0]
            # workspace
            p = os.path.join(workspace, IMAGES_ROOT, val)
            p = os.patchech.normpath(p)
            parent = p.rsplit('\\', 1)[0]
            if os.path.isdir(parent):
                if os.path.isfile(p):
                    cmd = '"%s" /select,"%s"' % ('explorer', p)
                else:
                    p = p.replace('.exr', '.jpg')
                    if os.path.isfile(p):
                        cmd = '"%s" /select,"%s"' % ('explorer', p)
                    else:
                        cmd = '"%s" "%s"' % ('explorer', parent)
            else:
                parent = parent.rsplit('\\', 1)[0]
                if os.path.isdir(parent):
                    cmd = '"%s" "%s"' % ('explorer', parent)
                else:
                    parent = parent.rsplit('\\', 1)[0]
                    if os.path.isdir(parent):
                        cmd = '"%s" "%s"' % ('explorer', parent)
            process = QProcess()
            process.startDetached(cmd)
        else:
            raise RuntimeError('File has not been saved. Unable to get path.')
cmd['rsuWindow_button14'] = rsuWindow_button14

def uvSnapshot(arg):
    """
    AutoConnect - Creates a UV Snapshot and tries to apply it to the assigned Photoshop document.
    """

    FILE_NAME = 'uv.jpg'
    RESOLUTION = 2048

    sel = getListSelection()
    ac = autoConnect.AutoConnect()

    if ac.PHOTOSHOP_PATH is None:
        raise WindowsError('Couldn\'t find Adobe Photoshop.')

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        if [f for f in ac.DATA.keys() if shaderName == f] == []:
            print '# Shader doesn\'t have an AutoConnect setup.'
            continue

        # Launch photoshop process
        editTexture(False)

        usedBy = rsShaderUtility.data[shaderName]['usedBy']
        parents = []
        for u in usedBy:
            parent = cmds.listRelatives(u, allParents=True, path=True)[0]
            parents.append(parent)
        cmds.select(parents)

        p = path.normpath(path.join(ac.workspace, ac.sourceImages, shaderName))
        if os.path.isdir(p) is not True:
            os.mkdir(p)
        else:
            print '# A folder already exists at this location. No files were created.'
        path.normpath(path.join(p, FILE_NAME))
        cmds.uvSnapshot(name=path.normpath(path.join(p, FILE_NAME)), overwrite=True, antiAliased=True, fileFormat='jpg', xResolution=RESOLUTION, yResolution=RESOLUTION)

        # Let's call Photoshop
        script = psCommand.script
        PS_SCRIPT = script.replace(
            '<UV_Image_Path>', path.normpath(path.join(p, FILE_NAME)).replace('\\', '\\\\')
        ).replace(
            '<Texture_PSD_Name>', '%s.psd'%(shaderName)
        )

        tempDir = tempfile.gettempdir()
        scriptFile = 'psScript.jsx'

        p = path.join(tempDir, scriptFile)
        f = open(p, 'w')
        f.write(PS_SCRIPT)
        f.close()

        cmd = '"%s" "%s"' % (path.normpath(ac.PHOTOSHOP_PATH), path.normpath(p) )
        process = QProcess()
        process.startDetached(cmd)
cmd['uvSnapshot'] = uvSnapshot

def rsFilterShaderList(arg):
    window.updateUI()
cmd['rsFilterShaderList'] = rsFilterShaderList

def rsFilterShaderList_off(arg):
    pass
cmd['rsFilterShaderList_off'] = rsFilterShaderList_off

def rsShaderScrollList_doubleClick():
    import maya.mel as mel
    global shaderOverrideMode
    global selectedShaderOverride

    sel = getListSelection()
    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        overrideShader = [f for f in shaderUtility.SHADER_OVERRIDE_OPTIONS if f['ui'] == selectedShaderOverride]
        if overrideShader == []:
            cmds.select(shaderName, replace=True)
            cmds.HypershadeWindow()
            cmds.evalDeferred('mel.eval(\'hyperShadePanelGraphCommand("hyperShadePanel1","showUpAndDownstream");\')')
            break
        else:
            for item in overrideShader:
                overrideShaderName =  '%s%s_%s' % (shaderName, item['suffix'], item['type'])
                if cmds.objExists(overrideShaderName) is True:
                    cmds.select(overrideShaderName, replace=True)
                    cmds.HypershadeWindow()
                    cmds.evalDeferred('mel.eval(\'hyperShadePanelGraphCommand("hyperShadePanel1","showUpAndDownstream");\')')
                break
cmd['rsShaderScrollList_doubleClick'] = rsShaderScrollList_doubleClick

def rsShaderScrollList_deleteKey():
    cmds.select(clear=True)
    sel = getListSelection()
    if sel is not None:
        for s in sel:
            shaderName = rsShaderUtility.customStringToShaderName(s)
            cmds.select(shaderName, add=True)
cmd['rsShaderScrollList_deleteKey'] = rsShaderScrollList_deleteKey

def rsShaderScrollList_onSelect(*args):
    """
    Function called when the a list item is selected
    Update setModes and current selection
    """

    sel = getListSelection()
    # ls = cmds.textScrollList('rsShaderScrollList', query=True, allItems=True)
    _currentSelection = []

    for s in sel:
        shaderName = rsShaderUtility.customStringToShaderName(s)
        if rsShaderUtility.data[shaderName]['standIn'] is not True:
            window.gwCustomRenamer.setOptionMenu1(value=shaderName.split('_')[0])
            window.gwCustomRenamer.setOptionMenu2(value=shaderName.split('_')[1])

        _currentSelection.append(shaderName)
    currentSelection=_currentSelection

    setPropertyOverridesMode()
    setShaderOverrideMode()
cmd['rsShaderScrollList_onSelect'] = rsShaderScrollList_onSelect

def postMenuCommand(*args):
    sel = getListSelection()
    if sel == []:
        for item in cmds.popupMenu(args[0], query=True, itemArray=True):
            cmds.menuItem(item, edit=True, enable=False)
    if sel != []:
        for item in cmds.popupMenu(args[0], query=True, itemArray=True):
            cmds.menuItem(item, edit=True, enable=True)
cmd['postMenuCommand'] = postMenuCommand

def rsArnoldPropertyOverridesCheckBox(arg):
    cmds.columnLayout('rsuWindow_columnLayout02', edit=True, visible=arg)
cmd['rsArnoldPropertyOverridesCheckBox'] = rsArnoldPropertyOverridesCheckBox

def _setOverrideValue(arg, index):
    global propertyOverridesMode
    setPropertyOverridesMode()

    sel = getListSelection()

    for s in sel:
        if propertyOverridesMode is True:
            shaderName = rsShaderUtility.customStringToShaderName(s)
            c = rsUtility.activeLayer.collection(shaderName.replace(':', '_'), isQuery=True)
            c.setOverrideValue(rsUtility.overrideAttributes[index]['long'], arg)

    rsUtility.overrideAttributes[index]['default'] = arg

    def update():
        if propertyOverridesMode is True:
            window.updateUI(updateRenderSetup=True)
        else:
            window.updateUI(updateRenderSetup=False)
    cmds.evalDeferred(update)

def _matList():
    matList = []
    for item in rsShaderUtility.data:
        matList.append(str(item))
    return util.natsort(matList)
def _matGroups():
    matList = _matList()
    def groupByPrefix(strings):
        stringsByPrefix = {}
        for string in strings:
            if '_' in string:
                prefix, suffix = map(str.strip, str(string).split("_", 1))
                if len(prefix) >= 2:
                    group = stringsByPrefix.setdefault(prefix, [])
                    group.append(suffix)
        dict = stringsByPrefix.copy()
        for key in dict:
            if len(dict[key]) <= 1:
                stringsByPrefix.pop(key, None)
        return stringsByPrefix
    groups = groupByPrefix(matList)
    groups[''] = []

    # sort dict - clunky, there must be a better way...
    keyList = util.natsort(groups.keys())
    return (keyList, groups)

def rsuWindow_checkbox02(arg):
    _setOverrideValue(arg, 0)
cmd['rsuWindow_checkbox02'] = rsuWindow_checkbox02

def rsuWindow_checkbox03(arg):
    _setOverrideValue(arg, 1)
cmd['rsuWindow_checkbox03'] = rsuWindow_checkbox03

def rsuWindow_checkbox04(arg):
    _setOverrideValue(arg, 2)
cmd['rsuWindow_checkbox04'] = rsuWindow_checkbox04

def rsuWindow_checkbox05(arg):
    _setOverrideValue(arg, 3)
cmd['rsuWindow_checkbox05'] = rsuWindow_checkbox05

def rsuWindow_checkbox06(arg):
    _setOverrideValue(arg, 4)
cmd['rsuWindow_checkbox06'] = rsuWindow_checkbox06

def rsuWindow_checkbox07(arg):
    _setOverrideValue(arg, 5)
cmd['rsuWindow_checkbox07'] = rsuWindow_checkbox07

def rsuWindow_checkbox08(arg):
    _setOverrideValue(arg, 6)
cmd['rsuWindow_checkbox08'] = rsuWindow_checkbox08

def rsuWindow_checkbox09(arg):
    _setOverrideValue(arg, 7)
cmd['rsuWindow_checkbox09'] = rsuWindow_checkbox09

def rsuWindow_checkbox10(arg):
    _setOverrideValue(arg, 8)
cmd['rsuWindow_checkbox10'] = rsuWindow_checkbox10

def rsuWindow_checkbox11(arg):
    """Shader override toggle"""
    cmds.columnLayout('rsuWindow_columnLayout03', edit=True, visible=arg)
cmd['rsuWindow_checkbox11'] = rsuWindow_checkbox11

# UI functions
def addScrollLayout(inTitle, parent, enable=True, visible=True):
    cmds.scrollLayout(
        inTitle,
        parent = parent,
        verticalScrollBarAlwaysVisible = False,
        width = WINDOW_WIDTH+6,
        height = WINDOW_HEIGHT,
        horizontalScrollBarThickness = SCROLLBAR_THICKNESS,
        verticalScrollBarThickness = SCROLLBAR_THICKNESS,
        enable = enable,
        visible = visible
    )
def addFrameLayout(inName, label, enable=True, marginWidth=FRAME_MARGIN[0], marginHeight=FRAME_MARGIN[1], collapsable=False, collapse=False, font='plainLabelFont', borderVisible=False, visible=True, labelVisible=True):
    cmds.frameLayout(
        inName,
        label = label,
        collapsable = collapsable,
        collapse = collapse,
        font = font,
        borderVisible = borderVisible,
        backgroundColor = FRAME_BACKGROUND,
        marginWidth = marginWidth,
        marginHeight = marginHeight,
        labelAlign = 'center',
        labelVisible = labelVisible,
        labelIndent = 0,
    )
def addRowLayout(inName, numberOfColumns,
                 columnAlign1 = '', columnAlign2 = ('',''), columnAlign3 = ('','',''), columnAlign4 = ('','','',''), columnAlign5 = ('','','','',''), columnAlign6 = ('','','','','',''),
                 columnAttach1 = '', columnAttach2 = ('',''), columnAttach3 = ('','',''), columnAttach4 = ('','','',''), columnAttach5 = ('','','','',''), columnAttach6 = ('','','','','',''),
                 columnWidth1 = 0, columnWidth2 = (0,0), columnWidth3 = (0,0,0), columnWidth4 = (0,0,0,0), columnWidth5 = (0,0,0,0,0), columnWidth6 = (0,0,0,0,0,0),
                 columnOffset1 = 0, columnOffset2 = (0,0), columnOffset3 = (0,0,0), columnOffset4 = (0,0,0,0), columnOffset5 = (0,0,0,0,0), columnOffset6 = (0,0,0,0,0,0),
                 enable = True, visible = True):
    cmds.rowLayout(
        inName,
        numberOfColumns = numberOfColumns,
        columnAlign1 = columnAlign1,
        columnAlign2 = columnAlign2,
        columnAlign3 = columnAlign3,
        columnAlign4 = columnAlign4,
        columnAlign5 = columnAlign5,
        columnAlign6 = columnAlign6,
        columnAttach1 = columnAttach1,
        columnAttach2 = columnAttach2,
        columnAttach3 = columnAttach3,
        columnAttach4 = columnAttach4,
        columnAttach5 = columnAttach5,
        columnAttach6 = columnAttach6,
        columnWidth1 = columnWidth1,
        columnWidth2 = columnWidth2,
        columnWidth3 = columnWidth3,
        columnWidth4 = columnWidth4,
        columnWidth5 = columnWidth5,
        columnWidth6 = columnWidth6,
        columnOffset1 = columnOffset1,
        columnOffset2 = columnOffset2,
        columnOffset3 = columnOffset3,
        columnOffset4 = columnOffset4,
        columnOffset5 = columnOffset5,
        columnOffset6 = columnOffset6,
        enable = enable,
        visible = visible
    )
def addOptionMenu(inName, label, inArr, changeCommand, enable=True, visible=True, size=(50,22)):
    cmds.optionMenu(
        inName,
        label = label,
        changeCommand = changeCommand,
        # width = size[0],
        height = size[1],
        enable = enable,
        visible = visible,
        alwaysCallChangeCommand = True)
    for a in inArr:
        cmds.menuItem(label = a)
def addButton(inTitle, label, command, size=(50,21), image = None, enable = True, visible = True):
    if image is None:
        cmds.button(
            inTitle,
            label = label,
            command = command,
            width = size[0],
            height = size[1],
            enable = enable,
            visible = visible
        )
    else:
        cmds.symbolButton(
            inTitle,
            command = command,
            width = size[0],
            height = size[1],
            image = image,
            enable = enable,
            visible = visible
        )
def addTextField(inTitle, placeholderText, enterCommand, textChangedCommand, changeCommand, enable = True, visible = True):
    cmds.textField(
        inTitle,
        placeholderText = placeholderText,
        enterCommand = enterCommand,
        textChangedCommand = textChangedCommand,
        changeCommand = changeCommand,
        editable = True,
        enable = enable,
        visible = visible
    )
def addText(inTitle, label, font='plainLabelFont'):
    cmds.text(
        inTitle,
        label = label,
        font = font
    )
def addSeparator(inTitle, height = 21, style = 'none', horizontal = True, enable = True, visible = True):
    cmds.separator(
        inTitle,
        height = height,
        style = style,
        horizontal = horizontal,
        enable = enable,
        visible = visible
    )
def addTextScrollList(inTitle, inArr, doubleClickCommand, selectCommand, deleteKeyCommand, enable = True, visible = True):
    cmds.textScrollList(
        inTitle,
        append = inArr,
        numberOfItems = len(inArr),
        numberOfRows = MIN_NUMBER_OF_ROWS,
        doubleClickCommand = doubleClickCommand,
        selectCommand = selectCommand,
        deleteKeyCommand=deleteKeyCommand,
        allowMultiSelection = True,
        enable = enable,
        visible = visible
    )
def addCheckBox(inTitle, label, offCommand, onCommand, value = False, enable = True, visible = True):
    cmds.checkBox(
        inTitle,
        label = label,
        offCommand = offCommand,
        onCommand = onCommand,
        value = value,
        enable = enable,
        visible = visible
    )
def addCheckboxes(integer1, integer2, parent, listItem):
    for index, item in enumerate(listItem):
        def inc(i): return str(index+i).zfill(2)
        cmds.setParent(parent)
        addRowLayout('rsuWindow_rowLayout'+inc(integer1), 2,
                        columnOffset2 = (20,0),
                        columnAlign2 = ('left','left'),
                        columnAttach2 = ('left','right'),
                        columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.85, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.15-1.0))
        addText('rsuWindow_text'+inc(integer2), item[0] + util.addChars(' ', 100))
        if item[0] is 'Matte':
            value = False
        else:
            value = True
        addCheckBox('rsuWindow_checkbox'+inc(integer2), '', item[1], item[2], value=value)

def _getQItem(string, QType):
    ptr = OpenMayaUI.MQtUtil.findControl(string)
    if ptr is None:
        return None
    else:
        return shiboken2.wrapInstance(long(ptr), QType)
def _getFullPath(QItem):
    layout = long(shiboken2.getCppPointer(QItem)[0])
    return OpenMayaUI.MQtUtil.fullName(layout)

class QGet(QtCore.QObject):
    def __init__(self, parent=None):
        super(QGet, self).__init__(parent=parent)

        ptr = OpenMayaUI.MQtUtil.mainWindow()
        mayaMainWindow = shiboken2.wrapInstance(long(ptr), QtWidgets.QMainWindow)
        self.allWidgets = QtWidgets.QApplication.allWidgets
        self.mayaMainWindow = mayaMainWindow
        self.QRenderView = None
        self.QRenderViewControl = None
        self.widget = None

    def _printInfo(self, obj):
        print '# objectName:'
        print obj.objectName()
        print '# windowTitle:'
        print obj.windowTitle()
        print '# Type:'
        print type(obj)
        print '# dir():'
        print dir(obj)
        print '# children():'
        print obj.children()
        print '# parent:'
        print obj.parent()

    def getQRenderView(self, printInfo=False, query=False):
        def _set():
            for obj in self.allWidgets():
                if type(obj) is QtWidgets.QMainWindow:
                    if obj.windowTitle() == 'Arnold Render View':
                        self.QRenderView = obj
                        break
            for obj in self.allWidgets():
                if type(obj) is QtWidgets.QWidget:
                    if obj.windowTitle() == 'Arnold RenderView':
                        self.QRenderViewControl = obj
                        break
        _set()
        if self.QRenderView is None and query is False:
            arnoldmenu.arnoldMtoARenderView()
            _set()

        if printInfo:
            self._printInfo(self.QRenderView)
        return self.QRenderView
    def getByWindowTitle(self, string):
        for obj in self.allWidgets():
            if type(obj) is QtWidgets.QWidget:
                if obj.windowTitle() == string:
                    self.widget = obj
        return self.widget
    def getByObjectName(self, string):
        for obj in self.allWidgets():
            if type(obj) is QtWidgets.QWidget:
                if obj.objectName() == string:
                    self.widget = obj
        return self.widget

class CustomRenamer(object):
    """
        The class enforces a naming convention when creating shaders and provides easy access
        to assign shaders to the current mesh selection.

        It also rename objects based on their shader assignment.
        Or, if no selection is present, renames shaders and their associated
        texture files (using the autoConnect rename() function)
    """


    OBJ_TYPES = {
        'transform': '_t',
        'mesh': 'Geo',
        'nurbsSurface': 'Geo',
        'nurbsCurve': 'Crv',
        'bezierCurve': 'Crv',
        'locator': 'Loc'
    }

    def __init__(self, newName='untitled'):
        self.newName = newName
        global rsShaderUtility
        rsShaderUtility = shaderUtility.ShaderUtility()
        self.shaderType = 'aiStandard'

        self.optionMenu1Sel = None
        self.optionMenu2Sel = None
        self.optionMenu3Sel = None

        self.textField1Sel = ''
        self.textField2Sel = ''
        self.textField3Sel = ''

        self.renderSetupUtilityWindow = None

    def setRenderSetupUtilityWindow(self, obj):
        self.renderSetupUtilityWindow = obj
        return self.renderSetupUtilityWindow

    def _filter(self, lst):
        """ Returns a filtered list accepting only the specified object types.
        The resulting list is reverse sorted, to avoid missing object names when renaming."""

        lst = list(set(lst)) # removes duplicate items
        if lst is None: return []
        arr = []
        for item in lst:
            for typ in [str(g) for g in self.__class__.OBJ_TYPES]:
                if cmds.objectType(item) == typ:
                    arr.append(item)

        arr.sort(key=lambda x: x.count('|'))
        return arr[::-1] # reverse list

    def setName(self, newName):
        self.newName = newName
        return self.newName

    def _children(self, name):
        children = cmds.listRelatives(name, fullPath=True, allDescendents=True)
        if children:
            return self._filter(children)
        else:
            return []

    def doIt(self):
        """ perform rename """

        def _getAssignedShader(name):
            dct = rsShaderUtility.data
            for key in dct.keys():
                for item in dct[key]['usedBy']:
                    if child in item:
                        return key


                # # assigned = [f for f in dct[key]['usedBy'] if name in f]
                # print assigned
                #     if assigned == []:
                #         return None
                #     return key

        sel = cmds.ls(selection=True, long=True)

        if not sel: return []
        if not self.newName: return []

        # Pull all objects in an array
        arr = []
        SELECTION = self._filter(sel)

        for s in SELECTION:
            children = self._children(s)
            if children:
                arr += children

        ALL_CHILDREN = self._filter(arr) # perform filter
        SELECTION = [item for item in SELECTION if item not in ALL_CHILDREN] # subtracting the children from the selection to avoid overlaps


        # First, let's rename all the children of the selected object

        for child in ALL_CHILDREN:

            # Find suffix
            suffix = [self.__class__.OBJ_TYPES[f] for f in self.__class__.OBJ_TYPES if f == cmds.objectType(child)][0]
            # newString = '%s%s_#'%(self.newName, suffix)

            if cmds.objectType(child) == 'transform': # check if the transform has a child of the appropiate type

                relatives = cmds.listRelatives(child, children=True)
                if relatives == []:
                    continue

                # Swap the new name if there's an appropiate shderAssignment
                if cmds.objectType(relatives[0]) == 'mesh':
                    shaderName = _getAssignedShader(child)
                    if shaderName is not None:
                        newString = '%s%s_#' % (
                            shaderName,
                            self.__class__.OBJ_TYPES[cmds.objectType(relatives[0])]
                        )
                        cmds.rename(child, newString, ignoreShape=False)
                        continue
                if cmds.objectType(relatives[0]) in self.__class__.OBJ_TYPES.keys():
                    newString = '%s%s_#' % (
                        self.newName,
                        self.__class__.OBJ_TYPES[cmds.objectType(relatives[0])]
                    )
                    cmds.rename(child, newString, ignoreShape=False)
                    continue

        # Lastly, let's rename the selected object itself
        for name in SELECTION:
            suffix = [self.__class__.OBJ_TYPES[f] for f in self.__class__.OBJ_TYPES if f == cmds.objectType(name)][0]
            newString = '%s%s_#'%(self.newName, suffix)
            cmds.rename(name, newString, ignoreShape=False)

        self.updateUI(updateWindow=True)

    def setOptionMenu1(self, value=''):

        cName = self.__class__.__name__
        optionMenu01Value = cmds.optionMenu('%s_optionMenu01'%(cName), query=True, value=True)

        items = cmds.optionMenu('%s_optionMenu01'%(cName), query=True, itemListShort=True)
        if items:
            for index, item in enumerate(items):
                label = cmds.menuItem(item, query=True, label=True)
                if label == value:
                    cmds.optionMenu('%s_optionMenu01'%(cName), edit=True, select=index+1)
        self.optionMenu01_changeCommand()

    def setOptionMenu2(self, value=''):

        cName = self.__class__.__name__
        optionMenu01Value = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, value=True)

        items = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, itemListShort=True)
        if items:
            for index, item in enumerate(items):
                label = cmds.menuItem(item, query=True, label=True)
                if label == value:
                    cmds.optionMenu('%s_optionMenu02'%(cName), edit=True, select=index+1)
        self.optionMenu02_changeCommand()

    def optionMenu01_changeCommand(self, *args):
        cName = self.__class__.__name__

        # Select group:
        optionMenu01Value = cmds.optionMenu('%s_optionMenu01'%(cName), query=True, value=True)
        textField = cmds.textField('%s_textField01'%(cName), edit=True, text=optionMenu01Value)

        # Populate children list:
        if optionMenu01Value is None:
            return
        optionMenu02Value = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, value=True)
        if optionMenu02Value is None:
            for item in util.natsort(rsShaderUtility.getShaderGroups()[optionMenu01Value]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'%(cName))
        else:
            for item in cmds.optionMenu('%s_optionMenu02'%(cName), query=True, itemListLong=True):
                cmds.deleteUI(item)
            for item in util.natsort(rsShaderUtility.getShaderGroups()[optionMenu01Value]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'%(cName))

        # Select group:
        optionMenu02Value = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, value=True)
        textField = cmds.textField('%s_textField02'%(cName), edit=True, text=optionMenu02Value)

    def optionMenu02_changeCommand(self, *args):
        cName = self.__class__.__name__
        value = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, value=True)
        textField = cmds.textField('%s_textField02'%(cName), edit=True, text=value)

    def optionMenu03_changeCommand(self, *args):
        cName = self.__class__.__name__
        value = cmds.optionMenu('%s_optionMenu03'%(cName), query=True, value=True)
        self.shaderType = value

    def makeNameString(self, *args):
        cName = self.__class__.__name__
        textField01 = cmds.textField('%s_textField01'%(cName), query=True, text=True)
        textField02 = cmds.textField('%s_textField02'%(cName), query=True, text=True)
        textField03 = cmds.textField('%s_textField03'%(cName), query=True, text=True)

        newName = ''
        if len(textField01) != 0:
            newName += textField01
        if len(textField02) != 0 and len(textField01) != 0:
            newName += '_'
            newName += textField02
        else:
            pass
        if len(textField01) != 0 and len(textField03) != 0:
            newName += textField03.capitalize()
        else:
            pass

        self.newName = newName
        return self.newName

    def createUI(self):
        cName = self.__class__.__name__
        windowID = '%sWindow'%(cName)
        windowTitle = '%sWindow'%(cName)
        WIDTH = WINDOW_WIDTH-(FRAME_MARGIN[0]*2)
        MARGIN = 0

        if cmds.workspaceControl(windowID, exists=True):
            cmds.deleteUI(windowID)

        sel = cmds.ls(selection=True)
        placeholderText = ''

        cmds.columnLayout('%s_columnLayout01'%(cName),
            parent='%s_frameLayout05' % ('RenderSetupUtilityWindow'),
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('left', 0),
            adjustableColumn=False,
            rowSpacing=0
        )

        if cmds.ls(selection=True):
            placeholder = cmds.ls(selection=True)[0]
        else:
            placeholder = 'newName'

        backgroundColor=[0.28]*3
        height=22

        # row1

        cmds.rowLayout(
            '%s_rowLayout02'%(cName),
            parent = '%s_columnLayout01'%(cName),
            numberOfColumns = 3,
            columnAlign3 = ('left','left','right'),
            columnAttach3 = ('both','both','both'),
            columnWidth3=((WIDTH/3),(WIDTH/3),(WIDTH/3)),
            height=height,
            enableBackground=True
        )
        cmds.optionMenu(
            '%s_optionMenu01'%(cName),
            label = '',
            changeCommand = self.optionMenu01_changeCommand,
            alwaysCallChangeCommand=True,
            height=height,
            enableBackground=True,
            backgroundColor=backgroundColor
        )
        cmds.optionMenu(
            '%s_optionMenu02'%(cName),
            label = '',
            changeCommand = self.optionMenu02_changeCommand,
            height = height,
            alwaysCallChangeCommand = True
        )
        cmds.optionMenu(
            '%s_optionMenu03'%(cName),
            label = '',
            changeCommand = self.optionMenu03_changeCommand,
            height = height,
            alwaysCallChangeCommand = True
        )

        # row2
        backgroundColor=(0.22,0.22,0.22)
        cmds.rowLayout(
            '%s_rowLayout01'%(cName),
            parent = '%s_columnLayout01'%(cName),
            numberOfColumns = 3,
            columnAlign3 = ('left','left','right'),
            columnAttach3 = ('both','both','both'),
            columnWidth3=((WIDTH/3),(WIDTH/3),(WIDTH/3.1)),
            width=WIDTH,
            enableBackground=True,
            backgroundColor=backgroundColor
        )
        cmds.textField(
            '%s_textField01'%(cName),
            placeholderText = 'Group Name',
            enterCommand = self.makeNameString,
            textChangedCommand = self.makeNameString,
            changeCommand = self.makeNameString,
            height=height,
            font='plainLabelFont',
            editable = True,
            enableBackground=True,
            backgroundColor=backgroundColor
        )
        cmds.textField(
            '%s_textField02'%(cName),
            placeholderText = 'Element Name',
            enterCommand = self.makeNameString,
            textChangedCommand = self.makeNameString,
            changeCommand = self.makeNameString,
            height=height,
            editable = True,
            font='plainLabelFont',
            enableBackground=True,
            backgroundColor=backgroundColor
        )
        cmds.textField(
            '%s_textField03'%(cName),
            placeholderText = 'Suffix (optional)',
            text = '',
            enterCommand = self.makeNameString,
            textChangedCommand = self.makeNameString,
            changeCommand = self.makeNameString,
            height=height,
            editable = True,
            font='plainLabelFont',
            enableBackground=True,
            backgroundColor=backgroundColor
        )

        # height=24
        cmds.separator(
            parent = '%s_columnLayout01'%(cName),
            style='none',
            height = 8
        )
        cmds.rowLayout(
            '%s_rowLayout03'%(cName),
            parent = '%s_columnLayout01'%(cName),
            numberOfColumns = 4,
            columnAlign4 = ('left','left','left','left'),
            columnAttach4 = ('both','both','both','right'),
            columnWidth4=((WIDTH/4),(WIDTH/4),(WIDTH/4),(WIDTH/4)),
            width=WIDTH
        )
        def rename(*args):
            dagSel = cmds.ls(selection=True)
            self.makeNameString()
            if dagSel != []:
                self.doIt()
                self.updateUI(updateWindow=True)
            if dagSel == []:
                ac = autoConnect.AutoConnect()
                sel = getListSelection()
                for s in sel:
                    shaderName = rsShaderUtility.customStringToShaderName(s)
                    ac.rename(shaderName, self.newName)
                self.updateUI(updateWindow=True)
        cmds.button(
            '%s_button01'%(cName),
            parent='%s_rowLayout03'%(cName),
            label = 'Rename',
            command = rename,
            height=height,
            enable=True
        )
        def assignShader(*args):
            self.makeNameString()

            sel = cmds.ls(selection=True)
            rel = cmds.listRelatives(sel, allDescendents=True, type='mesh', path=True)

            if cmds.objExists(self.newName) is True:
                pass
            else:
                print 'Shader \'%s\' doesn\'t exist. Skipping.' % self.newName
                return

            try:
                cmds.select(rel)
                cmds.hyperShade(assign=self.newName)
            except:
                pass
            cmds.select(sel)

            self.updateUI(updateWindow=True)
        cmds.button(
            '%s_button03'%(cName),
            parent='%s_rowLayout03'%(cName),
            label = 'Assign',
            command = assignShader,
            height=height,
            enable=True
        )
        def createShader(*args):

            self.makeNameString()

            sel = cmds.ls(selection=True)
            rel = cmds.listRelatives(sel, allDescendents=True, type='mesh', path=True)

            if cmds.objExists(self.newName) is True:
                print 'Shader \'%s\' already exists. Skipping.' % self.newName
                newShader = self.newName
                return None
            else:
                newShader = cmds.shadingNode(self.shaderType, asShader=True, name=self.newName)

                if cmds.objExists(str(newShader)+'SG'):
                    shading_group = str(newShader)+'SG'
                else:
                    shading_group = cmds.sets(name=str(newShader)+'SG', renderable=True, noSurfaceShader=True, empty=True)

            try:
                # Assign Shader
                cmds.select(rel)
                cmds.hyperShade(assign=newShader)
                cmds.select(sel)
            except:
                cmds.select(newShader)


            # Add PSD file
            addPSD = cmds.checkBox('%s_checkBox01'%(cName), query=True, value=True)
            if addPSD:
                ac = autoConnect.AutoConnect()
                ac.createPSDFile(newShader, apply=True)

            self.updateUI(updateWindow=True)
        cmds.button(
            '%s_button02'%(cName),
            parent='%s_rowLayout03'%(cName),
            label = 'Create',
            command = createShader,
            height=height,
            enable=True
        )
        cmds.checkBox(
            '%s_checkBox01'%(cName),
            label='Create PSD'
        )

    def updateUI(self, updateWindow=False):
        """
        Update the Custom Renamer module values
        """

        global window
        global rsUtility
        global rsShaderUtility

        rsShaderUtility = shaderUtility.ShaderUtility()
        rsUtility = utility.Utility()
        grps = rsShaderUtility.getShaderGroups()

        cName = self.__class__.__name__

        def selectOptionMenuItem(optionMenu, value):
            items = cmds.optionMenu(optionMenu, query=True, itemListShort=True)
            if items:
                for index, item in enumerate(cmds.optionMenu(optionMenu, query=True, itemListShort=True)):
                    label = cmds.menuItem(item, query=True, label=True)
                    if label == value:
                        cmds.optionMenu(optionMenu, edit=True, select=index+1)

        # Menu1
        value = cmds.optionMenu('%s_optionMenu01'%(cName), query=True, value=True)
        if value is not None:
            for item in cmds.optionMenu('%s_optionMenu01'%(cName), query=True, itemListLong=True):
                cmds.deleteUI(item)
        if grps.keys() != []:
            for item in util.natsort(grps.keys()):
                cmds.menuItem(label=item, parent='%s_optionMenu01'%(cName))
                if value is not None:
                    selectOptionMenuItem('%s_optionMenu01'%(cName), value)

        # Menu2
        key = cmds.optionMenu('%s_optionMenu01'%(cName), query=True, value=True)
        value = cmds.optionMenu('%s_optionMenu02'%(cName), query=True, value=True)
        if value is not None:
            for item in cmds.optionMenu('%s_optionMenu02'%(cName), query=True, itemListLong=True):
                cmds.deleteUI(item)
        if key is not None:
            for item in util.natsort(grps[key]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'%(cName))
                if value is not None:
                    selectOptionMenuItem('%s_optionMenu02'%(cName), cmds.textField('%s_textField02'%(cName), query=True, text=True))

        value = cmds.optionMenu('%s_optionMenu03'%(cName), query=True, value=True)
        if value is None:
            for item in shaderUtility.SHADER_TYPES:
                cmds.menuItem(item, label=item, parent='%s_optionMenu03'%(cName))

        # Update the main Render Setup Window to reflect new group assignments
        if updateWindow:
            cmds.evalDeferred(window.updateUI)

class RenderSetupUtilityWindow(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """
    Main class to create the Utility window.
    """

    toolName = windowID

    def __init__(self, parent=None):
        self.deleteInstances()

        super(RenderSetupUtilityWindow, self).__init__(parent=parent)
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        self.mayaMainWindow = shiboken2.wrapInstance(long(ptr), QtWidgets.QMainWindow)

        self.setWindowFlags(QtCore.Qt.Window)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        self.setWindowTitle('Render Setup Utility')
        self.setObjectName(self.__class__.toolName)

        # Set window Layout
        QVBoxLayout = QtWidgets.QVBoxLayout(self)
        QVBoxLayout.setObjectName('%s%s'%(self.__class__.toolName,'QVBoxLayout'))
        QVBoxLayout.setContentsMargins(0,0,0,0)
        QVBoxLayout.setSpacing(0)
        self.setLayout(QVBoxLayout)

        self.gwCustomRenamer = None

    def deleteInstances(self):
        # Delete child windows
        if cmds.window(windowNewLayerID, exists=True):
            cmds.deleteUI(windowNewLayerID)
        if cmds.window(windowNewShaderID, exists=True):
            cmds.deleteUI(windowNewShaderID)
        o = QGet()

        # Delete the workspaceControl
        control = self.__class__.toolName + 'WorkspaceControl'
        if cmds.workspaceControl(control, q=True, exists=True):
            cmds.workspaceControl(control, e=True, close=True)
            print 'Deleting control {0}'.format(control)
            cmds.deleteUI(control, control=True)

        # Delete the instance
        for obj in o.allWidgets():
            if type(obj) is QtWidgets.QWidget:
                if obj.objectName() == self.__class__.toolName:
                    cmds.workspaceControl(self.__class__.toolName + 'WorkspaceControl', query=True, exists=True)
                    print 'Deleting instance {0}'.format(obj)
                    # Delete it for good
                    obj.setParent(None)
                    obj.deleteLater()
    def createUI(self):
        """
        Main RenderSetupUtility ui function
        """

        o = QGet()
        layoutPath = _getFullPath(window.layout())
        cmds.setParent(layoutPath)

        #################################################
        # Render Layers
        addFrameLayout('%s_frameLayout01' % (self.__class__.__name__), 'Current Render Layer', collapsable=False, labelVisible=False)
        addRowLayout('%s_rowLayout01' % (self.__class__.__name__), 3,
                        columnAlign3 = ('left','left','right'),
                        columnAttach3 = ('left','both','right'),
                        columnWidth3 = (((WINDOW_WIDTH)-(FRAME_MARGIN[0]*2))*0.075,
                                        (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.85,
                                        (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.075))
        addButton('rsAddNewLayer', 'New', cmd['rsAddNewLayer'], image='RS_create_layer', size=(21,21))
        addOptionMenu('rsSelectLayer','', (), cmd['rsSelectLayer'])
        addButton('rsOpenRenderSetupWindow', 'Edit', cmd['rsOpenRenderSetupWindow'], image='render_setup.png', size=(21,21))
        #################################################
        # Collections
        cmds.setParent(layoutPath)
        addFrameLayout('%s_frameLayout02' % (self.__class__.__name__), 'Add Collections', labelVisible=False)
        addRowLayout(
            '%s_rowLayout02' % (self.__class__.__name__), 6,
            columnAlign6 = ('left','left','left','left','left','left'),
            columnAttach6 = ('both','both','right','right','right','right'),
            columnWidth6 = (
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.18,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.18,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.415,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.075,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.075,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.075
            )
       )
        addButton('rsAddCollection', 'Add', cmd['rsAddCollection'])
        addButton('rsRemoveCollection', 'Remove', cmd['rsRemoveCollection'])
        addButton('rsSelectShapes', 'Select Shapes', cmd['rsSelectShapes'], image='selectObject.png', size=(21,21))
        addButton('rsRenameShader', 'Rename Shader', cmd['rsRenameShader'], size=(21,21), image='QR_rename.png')
        addButton('rsDuplicateShader', 'Duplicate Shader', cmd['duplicateShader'], size=(21,21), image='newPreset.png')
        addButton('rsRefreshUI', 'Refresh', cmd['rsRefreshUI'], size=(21,21), image='QR_refresh.png')

        ############################
        # Filter List
        cmds.setParent('%s|%s_frameLayout02' % (layoutPath, self.__class__.__name__))
        addRowLayout('rsuWindow_rowLayout03', 2,
            columnAlign2 = ('left', 'right'),
            columnAttach2 = ('both', 'both'),
            columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.65, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.35))
        addTextField('rsFilterShaderList','Filter list...', cmd['rsFilterShaderList'], cmd['rsFilterShaderList_off'], cmd['rsFilterShaderList'])
        addOptionMenu('rsShaderGroups', '', (), cmd['rsShaderGroups'])


        ############################
        # The shaders scroll list

        cmds.setParent('%s|%s_frameLayout02'%(layoutPath, self.__class__.__name__))
        addRowLayout(
            '%s_rowLayout04' % (self.__class__.__name__), 1,
            columnAlign1 = 'left',
            columnAttach1 = 'both',
            columnWidth1 = WINDOW_WIDTH-(FRAME_MARGIN[0])
        )
        addTextScrollList('rsShaderScrollList', (), cmd['rsShaderScrollList_doubleClick'], cmd['rsShaderScrollList_onSelect'], cmd['rsShaderScrollList_deleteKey'])

        # Add popup menu:
        cmds.popupMenu(
            'rsShaderScrollListPopupMenu',
            parent = 'rsShaderScrollList',
            allowOptionBoxes=False,
            markingMenu=True,
            postMenuCommand=cmd['postMenuCommand']
        )
        cmds.menuItem('rsuWindow_popupMenuItem02', label='Duplicate Shader', command=cmd['duplicateShader'])
        cmds.menuItem( divider=True )
        cmds.menuItem('rsuWindow_popupMenuItem04', label='Graph Shader')
        cmds.menuItem( divider=True )
        cmds.menuItem('rsuWindow_popupMenuItem03', label='Select Shader')
        cmds.menuItem( divider=True )
        cmds.menuItem('rsuWindow_popupMenuItem05', label='Select Assigned Shapes')
        cmds.menuItem('rsuWindow_popupMenuItem06', label='Select Assigned Transforms')

        ###################################################
        # Arnold Property Overrides

        cmds.setParent('%s|%s_frameLayout02' % (layoutPath, self.__class__.__name__))
        cmds.columnLayout(
            'rsuWindow_columnLayout20',
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('left', 0),
            adjustableColumn=False,
            rowSpacing=0
        )
        cmds.separator(
            parent='rsuWindow_columnLayout20',
            height=4,
            style='none'
        )
        addRowLayout('rsuWindow_rowLayout05', 2,
                        columnAlign2 = ('left','both'),
                        columnAttach2 = ('left','right'),
                        columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.75, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.25))
        addText('rsuWindow_text01', 'Arnold Property Overrides', 'plainLabelFont')
        addCheckBox('rsArnoldPropertyOverridesCheckBox', '', cmd['rsArnoldPropertyOverridesCheckBox'], cmd['rsArnoldPropertyOverridesCheckBox'])
        cmds.separator(
            parent='rsuWindow_columnLayout20',
            height=4,
            style='none'
        )

        # Column Layout to toggle
        cmds.setParent('rsuWindow_columnLayout20')
        cmds.columnLayout(
            'rsuWindow_columnLayout02',
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('left', 0),
            adjustableColumn=False,
            rowSpacing=0
        )

        listItem = (
            ('Visible in Camera',       cmd['rsuWindow_checkbox02'], cmd['rsuWindow_checkbox02']),
            ('Visible in Diffuse',      cmd['rsuWindow_checkbox03'], cmd['rsuWindow_checkbox03']),
            ('Visible in Glossy',       cmd['rsuWindow_checkbox04'], cmd['rsuWindow_checkbox04']),
            ('Visible in Reflections',  cmd['rsuWindow_checkbox05'], cmd['rsuWindow_checkbox05']),
            ('Visible in Refractions',  cmd['rsuWindow_checkbox06'], cmd['rsuWindow_checkbox06']),
            ('Opaque',                  cmd['rsuWindow_checkbox07'], cmd['rsuWindow_checkbox07']),
            ('Cast Shadows',            cmd['rsuWindow_checkbox08'], cmd['rsuWindow_checkbox08']),
            ('Cast Self Shadows',       cmd['rsuWindow_checkbox09'], cmd['rsuWindow_checkbox09']),
            ('Matte',                   cmd['rsuWindow_checkbox10'], cmd['rsuWindow_checkbox10'])
        )
        addCheckboxes(7, 2, 'rsuWindow_columnLayout02', listItem)
        cmds.columnLayout('rsuWindow_columnLayout02', edit=True, visible=False)

        ##################################################
        # Shader Override
        cmds.setParent('%s|%s_frameLayout02' % (layoutPath, self.__class__.__name__))
        cmds.columnLayout(
            'rsuWindow_columnLayout21',
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('left', 0),
            adjustableColumn=False,
            rowSpacing=0
        )
        cmds.separator(
            parent = 'rsuWindow_columnLayout21',
            height = 4,
            style='none'
        )
        addRowLayout('rsuWindow_rowLayout06', 2,
                        columnAlign2 = ('left','right'),
                        columnAttach2 = ('left','right'),
                        columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.75, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.25))
        addText('rsuWindow_text11', 'Shader Override', 'plainLabelFont')
        addCheckBox('rsuWindow_checkbox11', '', cmd['rsuWindow_checkbox11'], cmd['rsuWindow_checkbox11'])
        cmds.separator(
            parent = 'rsuWindow_columnLayout21',
            height = 4,
            style='none'
        )

        cmds.setParent('rsuWindow_columnLayout21')
        cmds.columnLayout(
            'rsuWindow_columnLayout03',
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('both', 4),
            adjustableColumn=True,
            rowSpacing=0
        )
        cmds.setParent('rsuWindow_columnLayout03')
        addOptionMenu('rsuWindow_optionMenu02', 'Select: ', (), cmd['rsuWindow_optionMenu02'])

        global selectedShaderOverride
        selectedShaderOverride = shaderUtility.SHADER_OVERRIDE_OPTIONS[0]['ui'] # default selection
        cmds.columnLayout('rsuWindow_columnLayout03', edit=True, visible=False)

        ##################################################

        cmds.columnLayout(
            'rsuWindow_columnLayout04',
            parent=layoutPath,
            width=WINDOW_WIDTH-(FRAME_MARGIN[0]*2),
            columnAlign = 'left',
            columnAttach = ('both', 4),
            adjustableColumn=True,
            rowSpacing=0
        )


        ##################################################
        # Add & Assign Shader Groups
        cmds.setParent('rsuWindow_columnLayout04')
        addFrameLayout(
            '%s_frameLayout05' % (self.__class__.__name__),
            'Add & Assign Shader Groups',
            marginWidth=0,
            collapsable=True,
            collapse=True,
            labelVisible=True)
        # Add the renamer window
        self.gwCustomRenamer = CustomRenamer()
        self.gwCustomRenamer.createUI()
        self.gwCustomRenamer.updateUI(updateWindow=False)

        ##################################################
        # AutoConnect

        cmds.setParent('rsuWindow_columnLayout04')

        addFrameLayout(
            '%s_frameLayout03' % (self.__class__.__name__),
            'Adobe Connector',
            marginWidth=0,
            collapsable=True,
            collapse=True,
            labelVisible=True)
        addRowLayout(
            'rsuWindow_rowLayout07', 3,
            columnAlign3 = ('left','left','left'),
            columnAttach3 = ('both','both','both'),
            columnWidth3 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.4, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.3, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.3)
        )
        addButton('updateConnections', '> Update Connections <', cmd['updateConnections'])
        addButton('uvSnapshot', 'UV Snapshot', cmd['uvSnapshot'])
        addButton('editTexture', 'Edit Texture', cmd['editTexture'])

        # After Effects
        cmds.setParent('%s_frameLayout03' % (self.__class__.__name__))
        addRowLayout(
            'rsuWindow_rowLayout11', 2,
            columnAlign2 = ('left','left'),
            columnAttach2 = ('both','both'),
            columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.4, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.6)
        )
        addText('rsuWindow_text90', 'Send to After Effects:')
        addButton('makeComp', 'Send to After Effects', cmd['makeComp'])

        ##################################################
        # Render Setup /
        # Output settings

        cmds.setParent('rsuWindow_columnLayout04')
        addFrameLayout(
            '%s_frameLayout04' % (self.__class__.__name__),
            'Output Settings',
            marginWidth=0,
            collapsable=True,
            collapse=True,
            labelVisible=True
        )
        addRowLayout(
            'rsuWindow_rowLayout08', 1,
            columnAlign1 = 'center',
            columnAttach1 = 'both',
            columnWidth1 = WINDOW_WIDTH-(FRAME_MARGIN[0]*2)
        )
        addButton('rsuWindow_button14', 'Output path not set yet', cmd['rsuWindow_button14'])

        cmds.setParent('%s_frameLayout04' % (self.__class__.__name__))
        addRowLayout(
            'rsuWindow_rowLayout09', 3,
            columnAlign3 = ('left','right','right'),
            columnAttach3 = ('left','right','right'),
            columnWidth3 = (
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.8,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.14,
                (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.06
            )
        )
        addOptionMenu('rsuWindow_optionMenu05','', (), cmd['rsuWindow_optionMenu05'])
        addOptionMenu('rsuWindow_optionMenu04','', (), cmd['rsuWindow_optionMenu04'])
        cmds.menuItem(label='v001')

        cmds.setParent('rsuWindow_rowLayout09')
        addButton('rsuWindow_button12', '+1', cmd['rsuWindow_button12'], size=(21,21))

        cmds.setParent('%s_frameLayout04' % (self.__class__.__name__))
        addRowLayout(
            'rsuWindow_rowLayout10', 2,
            columnAlign2 = ('left','left'),
            columnAttach2 = ('both','right'),
            columnWidth2 = ((WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.7, (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.3)
        )
        addOptionMenu('rsuWindow_optionMenu03','Format:', (), cmd['rsuWindow_optionMenu03'])
        addOptionMenu('rsuWindow_optionMenu06','', (), cmd['rsuWindow_optionMenu06'])

        cmds.setParent('%s_frameLayout04' % (self.__class__.__name__))
        addRowLayout(
            'rsuWindow_rowLayout12', 4,
            columnAlign4 = ('right','left','right','left'),
            columnAttach4 = ('both','both','both','both'),
            columnWidth4 = (
                    (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.50,
                    (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.15,
                    (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.20,
                    (WINDOW_WIDTH-(FRAME_MARGIN[0]*2))*0.15,
                )
        )

        addText(
            '%s_setInFrameLabel' % (self.__class__.__name__),
            'In Frame '
        )
        addTextField(
            '%s_setInFrame' % (self.__class__.__name__),
            '',
            setInFrame,
            setInFrame,
            setInFrame
        )

        addText(
            '%s_setOutFrameLabel' % (self.__class__.__name__),
            'Out Frame '
        )
        addTextField(
            '%s_setOutFrame' % (self.__class__.__name__),
            '',
            setOutFrame,
            setOutFrame,
            setOutFrame
        )

    def updateUI(self, updateRenderSetup=False):
        """
        Update Render Setup Window and values
        """

        global rsUtility
        global rsShaderUtility


        # Pause qt draw temporarily
        QItem = _getQItem(windowID, QtWidgets.QWidget)
        QItem.setUpdatesEnabled(False)

        rsShaderUtility = shaderUtility.ShaderUtility()
        rsUtility = utility.Utility()
        window = _getQItem(self.__class__.toolName, QtWidgets.QWidget)

        self.gwCustomRenamer.updateUI(updateWindow=False)

        # Update Render layer Setup
        if updateRenderSetup is True:
            if rsUtility.activeLayer.needsRefresh():
                rsUtility.activeLayer.apply()

        # Housekeeping:
        rsUtility.removeMissingSelections()

        # Reapply style:
        windowStyle.apply(windowStyle)

        ##############################################
        # Render Layers
        listItem = []
        currentName = rsUtility.renderSetup.getVisibleRenderLayer().name()
        for l in rsUtility.renderSetup.getRenderLayers():
            listItem.append(l.name())

        QItem = window.findChild(QtWidgets.QWidget, 'rsSelectLayer')
        fullPath = _getFullPath(QItem)

        resetOptionMenu(fullPath, util.natsort(listItem), rl=True)
        selectOptionMenuItem(fullPath, currentName)

        if cmds.optionMenu(fullPath, q = True, value = True) == rsUtility.defaultName:
            QItem = window.findChild(QtWidgets.QWidget, 'rsAddCollection')
            fullPath = _getFullPath(QItem)
            cmds.button(fullPath, edit=True, enable=False)
            QItem = window.findChild(QtWidgets.QWidget, 'rsRemoveCollection')
            fullPath = _getFullPath(QItem)
            cmds.button(fullPath, edit=True, enable=False)
        else:
            QItem = window.findChild(QtWidgets.QWidget, 'rsAddCollection')
            fullPath = _getFullPath(QItem)
            cmds.button(fullPath, edit=True, enable=True)
            QItem = window.findChild(QtWidgets.QWidget, 'rsRemoveCollection')
            fullPath = _getFullPath(QItem)
            cmds.button(fullPath, edit=True, enable=True)
        ##############################################
        # Collections
        customStrings = []
        cleanList = []
        QItem = window.findChild(QtWidgets.QWidget, 'rsShaderScrollList')
        fullPath = _getFullPath(QItem)
        cmds.textScrollList(fullPath, edit=True, removeAll=True)
        def _spacer(inString):
            num = int(30-len(inString))
            if num > 0:
                # return util.addChars(' ', num)
                return '   '
            else:
                return ' '

        # Loop through shader list
        for shaderName in rsShaderUtility.data.keys():
            c = rsUtility.activeLayer.collection(shaderName.replace(':', '_'), isQuery=True)

            # Mark item as inactive if not in the collections list
            if c is None:

                # Set the custom string of the shader.
                # The custom string used by the Qt delegate for custom display and to indicate if the item is active or inactive.
                rsShaderUtility.data[shaderName]['customString'] = '%s%s%s)' % (
                    shaderName,
                    ' ',
                    '(' + str(len(rsShaderUtility.data[shaderName]['usedBy']))
                )

            # Mark item as active if in the collections list
            else:

                # Get current override values
                for index, item in enumerate(rsUtility.overrideAttributes):
                    try:
                        rsUtility.overrideAttributes[index][item['default']] = c.getOverrideValue(item['long'])
                    except:
                        print('# Couldn\'t get attribute value for ' + item['long'] + '.')

                def _get(item):
                    val = c.getOverrideValue(item['long'])
                    if val is None:
                        return ''
                    else:
                        return item['custom'][1-val]

                # Add warning if usedBy doesn't match collection selection
                WARNING = ''
                if c.selection.asList() != list(rsShaderUtility.data[shaderName]['usedBy']):
                    WARNING = '!!'
                SHADER_OVERRIDE = ''
                if _hasOverride(shaderName):
                    SHADER_OVERRIDE = '#'
                rsShaderUtility.data[shaderName]['customString'] = '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % (
                    ACTIVEITEM_PREFIX,
                    shaderName,
                    _spacer(ACTIVEITEM_PREFIX + shaderName),
                    _get(rsUtility.overrideAttributes[5]),
                    _get(rsUtility.overrideAttributes[0]),
                    _get(rsUtility.overrideAttributes[1]),
                    _get(rsUtility.overrideAttributes[2]),
                    _get(rsUtility.overrideAttributes[3]),
                    _get(rsUtility.overrideAttributes[4]),
                    _get(rsUtility.overrideAttributes[6]),
                    _get(rsUtility.overrideAttributes[7]),
                    _get(rsUtility.overrideAttributes[8]),
                    str(len(rsShaderUtility.data[shaderName]['usedBy'])),
                    WARNING,
                    SHADER_OVERRIDE
                )
            customStrings.append(rsShaderUtility.data[shaderName]['customString'])
            cleanList.append(shaderName)

        # Re-Set selected items from saved selection.
        matches = set([])
        global currentSelection
        if currentSelection is not None:
            matches = set(currentSelection).intersection(set(cleanList))

        QItem = window.findChild(QtWidgets.QWidget, 'rsFilterShaderList')
        fullPath = _getFullPath(QItem)
        filter = cmds.textField(fullPath, query=True, text=True)

        filteredList = [s for s in customStrings if filter.lower() in s.lower()]
        QItem = window.findChild(QtWidgets.QWidget, 'rsShaderScrollList')
        fullPath = _getFullPath(QItem)
        for item in util.natsort(filteredList, filterOn=True):
            cmds.textScrollList(fullPath, edit=True, append=item)
        for match in matches:
            cmds.textScrollList(fullPath, edit=True, selectItem=rsShaderUtility.data[match]['customString'])
        # Set height
        _setTextScrollListVisibleItemNumber()

        # Style scrollist
        numItems = len(filteredList)
        windowStyle.apply(windowStyle)

        # Checkboxes
        global propertyOverridesMode
        propertyOverridesMode = setPropertyOverridesMode()

        # Shader Overrides
        listItem = []
        menuName = 'rsuWindow_optionMenu02'
        for item in shaderUtility.SHADER_OVERRIDE_OPTIONS:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)
        setShaderOverrideMode()

        ##############################################
        # Filter list
        resetOptionMenu('rsShaderGroups', _matGroups()[0], rl=False)
        filterListText = cmds.textField('rsFilterShaderList', query=True, text=True)
        selectOptionMenuItem('rsShaderGroups', filterListText, rl=False)

        #############################################
        # Render output templates
        # Output format
        listItem = []
        menuName = 'rsuWindow_optionMenu03'
        for item in renderOutput.SIZE_TEMPLATE:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)
        # Check current resolution
        currentWidth = cmds.getAttr('%s.width' % renderOutput.RESOLUTION_NODE)
        currentHeight = cmds.getAttr('%s.height' % renderOutput.RESOLUTION_NODE)

        # Check if the current list corresponds to any of the predefined sizes
        current = [w for w in renderOutput.SIZE_TEMPLATE if currentWidth == w['width'] and currentHeight == w['height']]
        if current:
            selectOptionMenuItem(menuName, current[0]['ui'])

        _outputTemplate()

        # Playback speed
        # Populate list
        listItem = []
        menuName = 'rsuWindow_optionMenu06'
        for item in renderOutput.TIME_TEMPLATE:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)
        # Get current option
        currentTime = cmds.currentUnit(query=True, time=True)
        current = [t for t in renderOutput.TIME_TEMPLATE if currentTime == t['name']]
        if current:
            selectOptionMenuItem('rsuWindow_optionMenu06', current[0]['ui'])

        # In and out frames:
        cmds.textField(
            '%s_setInFrame' % (self.__class__.__name__),
            edit=True,
            text=int(cmds.getAttr('defaultRenderGlobals.startFrame'))
        )
        cmds.textField(
            '%s_setOutFrame' % (self.__class__.__name__),
            edit=True,
            text=int(cmds.getAttr('defaultRenderGlobals.endFrame'))
        )

        QItem = _getQItem(windowID, QtWidgets.QWidget)
        QItem.setUpdatesEnabled(True)

class WindowStyle(QtWidgets.QStyledItemDelegate):
    """
    Custom ui and delegate for model.
    """

    ROW_HEIGHT = 26
    FONT_PIXEL_SIZE = ROW_HEIGHT / 2.3636
    FONT_PIXEL_SIZE_OFFSET = (FONT_PIXEL_SIZE + 1) / 2
    ROW_WIDTH = WINDOW_WIDTH - (FRAME_MARGIN[0] * 2) - 6

    def __init__(self, parent=None, *args):
        super(WindowStyle, self).__init__(parent=parent)
        # QtWidgets.QStyledItemDelegate.__init__(self, parent=parent, *args)

        self.warningIcon = tempfile.gettempdir()+'\RS_warning.png'
        cmds.resourceManager(saveAs=['RS_warning.png', self.warningIcon])
        self.shaderOverrideIcon = tempfile.gettempdir()+'\out_shadingEngine.png'
        cmds.resourceManager(saveAs=['out_shadingEngine.png', self.shaderOverrideIcon])


    def sizeHint(self, option, index):
        return QtCore.QSize( self.__class__.ROW_WIDTH, self.__class__.ROW_HEIGHT)

    def paint(self, painter, option, index):
        """
        Main paint function for the Render Setup Utility
        """

        QItem = _getQItem('rsShaderScrollList', QtWidgets.QListWidget)
        fullPath = _getFullPath(QItem)

        # Reset pen
        painter.save()
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        # Set font
        font = QtGui.QFont()
        font.setFamily('Segoe UI')
        font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
        font.setItalic(False)
        painter.setFont(font)

        # UI Properties
        leadRectangleWidth = 6
        leadTextMargin = (leadRectangleWidth * 2) + 3
        textSpacer = 6

        # Items
        allItems = cmds.textScrollList('rsShaderScrollList', query=True, allItems=True)
        item = allItems[index.row()]
        value = index.data(QtCore.Qt.DisplayRole)


        # Check weather the shader is in part of the ShaderUtility.
        # I noticed sometimes with updateUI there is a ltency whilst the shaderUtility updates,
        # hence I get paint errors.
        try:
            rsShaderUtility.data[rsShaderUtility.customStringToShaderName(item)]
        except:
            return False

        # Check if item is an environment shader
        try:
            isEnvironment = rsShaderUtility.data[rsShaderUtility.customStringToShaderName(item)]['environment']
        except:
            isEnvironment = False
            print '# Error getting environment attribute for %s #' % item

        # Getting information about the item
        shaderName = rsShaderUtility.customStringToShaderName(value, properties=False)
        nameSpace = rsShaderUtility.data[shaderName]['nameSpace']
        shaderType = rsShaderUtility.data[shaderName]['type']
        attr = rsShaderUtility.customStringToShaderName(value, properties=True)

        # Getting visual width of the text to be drawn
        shaderNameWidth = QtGui.QFontMetrics(font).width(shaderName.split(':')[-1]) # in Maya 2017 update 4 I'm not getting the ':' anymore..
        nameSpaceWidth = QtGui.QFontMetrics(font).width(nameSpace)

        # Draw active items
        if rsShaderUtility.isActive(item):
            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82,133,166)))
                painter.drawRect(option.rect)
            else:
                if isEnvironment:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(82,92,102)))
                    painter.drawRect(option.rect)
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(82,82,82)))
                    painter.drawRect(option.rect)

            painter.setBrush(QtGui.QBrush(QtGui.QColor(255,170,100)))
            painter.drawRect(
                QtCore.QRect(
                    option.rect.left(),
                    option.rect.top(),
                    leadRectangleWidth,
                    option.rect.height()
                )
            )

            # Draw namespace
            if nameSpace != ':': # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace
                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(75,75,75)))
                    painter.drawRect(
                        QtCore.QRect(
                            leadRectangleWidth,
                            option.rect.top(),
                            nameSpaceWidth + leadTextMargin,
                            option.rect.height()
                        )
                    )

                # Draw namespace
                painter.setPen(QtGui.QPen(QtGui.QColor(150,150,150)))
                font.setBold(False)
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        leadTextMargin, # vertical offset
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width(),
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignLeft,
                    '%s' % (nameSpace)
                )

            # Draw shader name
            painter.setPen(QtGui.QPen(QtGui.QColor(210,210,210)))
            font.setBold(True)
            painter.setFont(font)

            painter.drawText(
                QtCore.QRect(
                    (textSpacer*2 if nameSpace != '' else 0) + leadTextMargin + nameSpaceWidth, # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderName.split(':')[-1])
            )

            # Draw shader type
            painter.setPen(QtGui.QPen(QtGui.QColor(150,150,150)))
            font.setPixelSize(10)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRect(
                    (textSpacer*2 if nameSpace != '' else 0) + leadTextMargin + nameSpaceWidth + shaderNameWidth + textSpacer, # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderType)
            )

            # Draw warning icon
            if '!!' in attr:
                QIcon = QtGui.QImage(self.warningIcon)
                if isEnvironment is False:
                    painter.drawImage(
                        QtCore.QPoint(
                            (self.__class__.FONT_PIXEL_SIZE_OFFSET / 2) * 3,
                            option.rect.top() + (self.__class__.FONT_PIXEL_SIZE_OFFSET / 2)
                        ),
                    QIcon)
                attr = attr.replace('!!','')

            # If the item is a mask append a small black rectangle to mark it
            if 'M-' in attr:
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QBrush(QtGui.QColor(50,50,50)))
                painter.drawRect(
                    QtCore.QRect(
                        leadRectangleWidth,
                        option.rect.top(),
                        leadRectangleWidth,
                        option.rect.height()
                    )
                )

            # Arnold shader override and attributes
            painter.setPen(QtGui.QPen(QtGui.QColor(210,210,210)))
            font.setBold(False)
            painter.setFont(font)

            if '#' in attr: # check if the item is being overriden by a shader

                # Shader override icon
                QIcon = QtGui.QImage(self.shaderOverrideIcon)
                painter.drawImage(
                    QtCore.QPoint(
                        option.rect.width() - 22,
                        option.rect.top() + 3),
                    QIcon
                )

                # Remove shader override character and draw arnold attributes
                attr = attr.replace('#','')

                painter.drawText(
                    QtCore.QRect(
                        0,
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width() - 24,
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignRight,
                    attr
                )
            else:
                painter.drawText(
                    QtCore.QRect(
                        leadTextMargin,
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width() - 22,
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignRight,
                    attr
                )

        # # Inactive items
        # if rsShaderUtility.isActive(item) is not True:
        #     if option.state & QtWidgets.QStyle.State_Selected:
        #         painter.setFont(font)
        #         painter.setBrush(QtGui.QBrush(QtGui.QColor(82,133,166)))
        #         painter.drawRect(option.rect)
        #     else:
        #         painter.setFont(font)
        #
        #         if isEnvironment:
        #             painter.setBrush(QtGui.QBrush(QtGui.QColor(55,67,77)))
        #             painter.drawRect(option.rect)
        #         else:
        #             painter.setBrush(QtGui.QBrush(QtGui.QColor(55,55,55)))
        #             painter.drawRect(option.rect)
        #
        #     # Draw shader name
        #     font.setBold(False)
        #     painter.setPen(QtGui.QPen(QtGui.QColor(230,230,230)))
        #
        #     painter.drawText(
        #         QtCore.QRect(
        #             leadTextMargin,
        #             option.rect.top() + 7,
        #             self.__class__.ROW_WIDTH - 22,
        #             option.rect.height() - 7),
        #         QtCore.Qt.AlignLeft,
        #         shaderName.split(':')[-1]
        #     )
        #
        #     if nameSpace != ':':
        #         shaderNameWidth = QtGui.QFontMetrics(font).width(shaderName.split(':')[-1])
        #         painter.setPen(QtGui.QPen(QtGui.QColor(150,150,150)))
        #         font.setBold(False)
        #         painter.setFont(font)
        #
        #         painter.drawText(
        #             QtCore.QRect(
        #                 leadTextMargin + shaderNameWidth + 5,
        #                 option.rect.top() + 6,
        #                 option.rect.width(),
        #                 option.rect.height() - 6),
        #             QtCore.Qt.AlignLeft,
        #             '%s' % nameSpace
        #         )
        #
        #     try:
        #         painter.setPen(QtGui.QPen(QtGui.QColor(210,210,210)))
        #         painter.setFont(font)
        #
        #         painter.drawText(
        #             QtCore.QRect(
        #                 leadTextMargin,
        #                 option.rect.top() + 7,
        #                 option.rect.width() - 22,
        #                 option.rect.height() - 7),
        #             QtCore.Qt.AlignRight,
        #             attr[1:][:-1]
        #         )
        #
        #     except:
        #         raise RuntimeError('Error drawing text.')
        #
        #

        # !!! Draw active items
        if rsShaderUtility.isActive(item) is False:
            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82,133,166)))
                painter.drawRect(option.rect)
            else:
                if isEnvironment:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(55,67,77)))
                    painter.drawRect(option.rect)
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(55,55,55)))
                    painter.drawRect(option.rect)



            # Draw namespace
            if nameSpace != ':': # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace
                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(50,50,50)))
                    painter.drawRect(
                        QtCore.QRect(
                            leadRectangleWidth,
                            option.rect.top(),
                            nameSpaceWidth + leadTextMargin,
                            option.rect.height()
                        )
                    )

                # Draw namespace rectangle and text
                painter.setPen(QtGui.QPen(QtGui.QColor(100,100,100)))
                font.setBold(False)
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        leadTextMargin, # vertical offset
                        option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                        option.rect.width(),
                        option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                    QtCore.Qt.AlignLeft,
                    '%s' % (nameSpace)
                )

            # Draw shader name
            painter.setPen(QtGui.QPen(QtGui.QColor(150,150,150)))
            font.setBold(False)
            painter.setFont(font)

            painter.drawText(
                QtCore.QRect(
                    (textSpacer*2 if nameSpace != '' else 0) + leadTextMargin + nameSpaceWidth, # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderName.split(':')[-1])
            )

            # Draw shader type
            painter.setPen(QtGui.QPen(QtGui.QColor(100,100,100)))
            font.setPixelSize(10)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRect(
                    (textSpacer*2 if nameSpace != '' else 0) + leadTextMargin + nameSpaceWidth + shaderNameWidth + textSpacer, # adding text spacing then there's a name space drawn
                    option.rect.top() + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                    option.rect.width(),
                    option.rect.height() - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                QtCore.Qt.AlignLeft,
                '%s' % (shaderType)
            )

            try:
                painter.setPen(QtGui.QPen(QtGui.QColor(210,210,210)))
                painter.setFont(font)

                painter.drawText(
                    QtCore.QRect(
                        leadTextMargin,
                        option.rect.top() + 7,
                        option.rect.width() - 22,
                        option.rect.height() - 7),
                    QtCore.Qt.AlignRight,
                    attr[1:][:-1]
                )

            except:
                raise RuntimeError('Error drawing text.')



        painter.restore()

    def apply(self, delegate):
        """
        Qt: Applies custom UI.

        """

        window = _getQItem(windowID, QtWidgets.QWidget)
        window.layout().setSpacing(0)
        window.layout().addStretch(1)

        QItem = _getQItem('%s_frameLayout01' % ('RenderSetupUtilityWindow'), QtWidgets.QWidget)
        # QItem.setFixedHeight(40)
        QItem.setStyleSheet(
            'QWidget {\
                padding:0;\
                margin:0;\
            }'
        )


        QItem = _getQItem('rsShaderScrollList', QtWidgets.QListWidget)
        fullPath = _getFullPath(QItem)

        QSize = QtCore.QSize(delegate.ROW_WIDTH, delegate.ROW_HEIGHT)
        for i in range(QItem.count()):
            QItem.setItemDelegateForRow(i, delegate)
            QItem.item(i).setSizeHint(QSize)
        QItem.setStyleSheet(
            'QListWidget {\
                padding:0;\
                margin:0;\
                color: rgb(200,200,200);\
                background-color:rgb(60,60,60);\
                border-style:solid;\
                border-radius:2\
            }'
        )

        # Filter list
        QItem = _getQItem('rsuWindow_rowLayout03', QtWidgets.QWidget)
        QItem.setStyleSheet(
            '.QWidget {\
                background-color: rgb(60,60,60);\
                color: rgb(200,200,200);\
                padding:1 0;\
                margin:0;\
                border-radius:2px\
        }')

        # Arnold Propery / Shader Overrides
        for item in ['rsuWindow_columnLayout20', 'rsuWindow_columnLayout21']:
            QItem = _getQItem(item, QtWidgets.QWidget)
            QItem.setStyleSheet(
                '.QWidget {\
                    background-color: rgb(60,60,60);\
                    color: rgb(200,200,200);\
                    padding: 4px 0px 2px 4px;\
                    margin: 0;\
                    border-radius:2px\
                }\
                QWidget {\
                    padding: 0 4;\
                }'\
            )

        for item in ['rsSelectLayer', 'rsuWindow_optionMenu02', 'rsuWindow_optionMenu03', 'rsuWindow_optionMenu04']:
            QItem = _getQItem(item, QtWidgets.QComboBox)
            QItem.setStyleSheet(
                'QComboBox {\
                    color: rgb(200,200,200);\
                    background-color: rgb(95,95,95);\
                    padding:0 4px 0 4px;\
                    margin:0;\
                }\
                QComboBox QAbstractItemView  {\
                    padding: 0;\
                    border-width: 0;\
                    border-style: none;\
                }'
            )
        for item in ['CustomRenamer_optionMenu01', 'CustomRenamer_optionMenu02', 'CustomRenamer_optionMenu03']:
            QItem = _getQItem(item, QtWidgets.QComboBox)
            QItem.setStyleSheet(
                'QComboBox {\
                    color: rgb(200,200,200);\
                    background-color: rgb(68,68,68);\
                    padding:0 4px 0 0;\
                    margin:0;\
                    }\
                QComboBox QAbstractItemView {\
                    border-width:0;\
                    border-style: none;\
                }'
            )

        # Buttons
        def setButtonStylesheet(inName, eColor, eBackgroundColor, ehColor, ehBackgroundColor):
            QItem = _getQItem(inName, QtWidgets.QPushButton)
            QItem.setStyleSheet('QPushButton {\
                color: rgb(%s);\
                background-color: rgb(%s);\
                border: none;\
                border-radius: 2px;\
                font-size:12px\
            }\
            QPushButton:hover {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }\
            QPushButton:disabled {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }' % (eColor, eBackgroundColor, ehColor, ehBackgroundColor, dColor, dBackgroundColor))
        def setAdobeButtonStylesheet(inName, eColor, eBackgroundColor, ehBackgroundColor):
            QItem = _getQItem(inName, QtWidgets.QPushButton)
            QItem.setStyleSheet('QPushButton {\
                color: rgb(%s);\
                background-color: rgb(%s);\
                border: solid;\
                border-color: rgb(%s);\
                border-width: 1px;\
                border-radius: 2px;\
                font-size:11px\
            }\
            QPushButton:hover {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }\
            QPushButton:disabled {\
                color: rgb(%s);\
                background-color: rgb(%s)\
            }' % (eColor, eBackgroundColor, eColor, eColor, ehBackgroundColor, eColor, eBackgroundColor))

        eColor = '200,200,200'
        eBackgroundColor = '95,95,95'
        ehColor = '230,230,230'
        ehBackgroundColor = '100,100,100'
        dColor = '95,95,95'
        dBackgroundColor = '68,68,68'

        for item in ['rsAddCollection','rsRemoveCollection','updateConnections','rsuWindow_button12', 'CustomRenamer_button01', 'CustomRenamer_button02', 'CustomRenamer_button03']:
            setButtonStylesheet(item, eColor, eBackgroundColor, ehColor, ehBackgroundColor)
        for item in ['editTexture','uvSnapshot']:
            setAdobeButtonStylesheet(item, '27, 198, 251', '0,29,38', '0,39,48')
        setAdobeButtonStylesheet('makeComp', '198,140,248', '31,0,63', '41,0,73')

        for item in ['rsFilterShaderList', 'CustomRenamer_textField01', 'CustomRenamer_textField02', 'CustomRenamer_textField03']:
            QItem = _getQItem(item, QtWidgets.QLineEdit)
            QItem.setStyleSheet('QLineEdit {\
                background-color: rgb(60,60,60);\
                padding:2 2;\
                margin:0;\
            }')

        def setTextStylesheet(inName, margin, borderColor):
            QItem = _getQItem(inName, QtWidgets.QLabel)
            QItem.setStyleSheet('QLabel {\
                border-style: dashed;\
                border-width: 0 0 1px 0;\
                border-color: rgb(50,50,50);\
                color: rgb(175,175,175);\
                font-size: 10px;\
                margin-left: 0;\
                margin-bottom: 2\
            }')
        margin = '2'
        borderColor = '55,55,55'
        for item in ['rsuWindow_text02','rsuWindow_text03','rsuWindow_text04','rsuWindow_text05','rsuWindow_text06',
            'rsuWindow_text07','rsuWindow_text08','rsuWindow_text09','rsuWindow_text10']:
            setTextStylesheet(item, borderColor, margin)

        QItem = _getQItem('rsuWindow_button14', QtWidgets.QPushButton)
        QItem.setStyleSheet('QPushButton {\
            color: rgb(150,150,150);\
            background-color: rgb(50,50,50);\
            border: none;\
            border-radius: 2px;\
            font-size:12px\
        }')

        QItem = _getQItem('rsShaderGroups', QtWidgets.QComboBox)
        QItem.setStyleSheet('QComboBox {\
            color: rgb(150,150,150);\
            background-color: rgb(60,60,60);\
            border: none;\
            border-radius: 2px;\
            font-size:11px\
            }\
            QComboBox::drop-down {\
            background-color: rgb(58,58,58);\
            border: none;\
            }'
        )

class EventFilter(QtCore.QObject):
    """
    Event filter which emits a parent_closed signal whenever
    the monitored widget closes.

    via:
    https://github.com/shotgunsoftware/tk-maya/blob/master/python/tk_maya/panel_util.py
    """

    def set_associated_widget(self, widget_id):
        """
        Set the widget to effect
        """
        self._widget_id = widget_id

    def eventFilter(self, obj, event):
        """
        QT Event filter callback

        :param obj: The object where the event originated from
        :param event: The actual event object
        :returns: True if event was consumed, False if not
        """

        global propertyOverridesMode
        propertyOverridesMode = False
        # if event.type() == QtCore.QEvent.Type.WindowDeactivate:
            # cmds.textScrollList('rsShaderScrollList', edit=True, deselectAll=True)
            # propertyOverridesMode = setPropertyOverridesMode()
            # setShaderOverrideMode()
        return False

def createUI():
    # Let's make sure arnold is loaded and that the arnold options are created.
    import mtoa.core as core
    core.createOptions()

    global window
    global windowStyle

    # global DagObjectCreatedID
    # global NameChangedID
    # global SceneOpenedID
    # global SceneImportedID
    # global SceneSegmentChangedID

    window = RenderSetupUtilityWindow()

    window.show(dockable=True)
    window.createUI()
    windowStyle = WindowStyle(parent=window)

    cmds.workspaceControl(RenderSetupUtilityWindow.toolName + 'WorkspaceControl', edit=True, widthProperty='fixed')

    # Event filters for the window.
    # ef = EventFilter(window)
    # ef.set_associated_widget(window)
    # window.installEventFilter(ef)

    window.updateUI(updateRenderSetup=False)

    # DagObjectCreatedID = OpenMaya.MEventMessage.addEventCallback("DagObjectCreated", _DagObjectCreatedCB, clientData=window)
    # NameChangedID = OpenMaya.MEventMessage.addEventCallback("NameChanged", _NameChangedCB, clientData=window)
    # SceneOpenedID = OpenMaya.MEventMessage.addEventCallback("SceneOpened", _SceneOpenedCB, clientData=window)
    # SceneImportedID = OpenMaya.MEventMessage.addEventCallback("SceneImported", _SceneImportedCB, clientData=window)
    # SceneSegmentChangedID = OpenMaya.MEventMessage.addEventCallback("SceneSegmentChanged", _SceneSegmentChangedCB, clientData=window)
