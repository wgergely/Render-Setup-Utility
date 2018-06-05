# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, R0913
# pylint: disable=

"""
Modules to define the script ui.
"""

import base64
import functools
import os
import os.path as path
import re
import tempfile

import shiboken2

import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
from PySide2.QtCore import QProcess

import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.views.renderSetup as renderSetupUI
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as OpenMayaUI
import RenderSetupUtility
import RenderSetupUtility.ac.aeCommand as aeCommand
import RenderSetupUtility.ac.autoConnect as autoConnect
import RenderSetupUtility.ac.psCommand as psCommand
import RenderSetupUtility.ac.templates as templates
import RenderSetupUtility.main.renderOutput as renderOutput
import RenderSetupUtility.main.utilities as util
import RenderSetupUtility.main.utility as utility
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from RenderSetupUtility.main.shaderUtility import SHADER_OVERRIDE_OPTIONS, \
    SHADER_TYPES, ShaderUtility

# pylint: disable=C0103

WINDOW_WIDTH = 360
WINDOW_HEIGHT = 150
WINDOW_BACKGROUND = (0.22, 0.22, 0.22)
FRAME_BACKGROUND = (0.245, 0.245, 0.245)
FRAME_MARGIN = 1
SCROLLBAR_THICKNESS = 6
ACTIVEITEM_PREFIX = ' '
COLLECTION_SUFFIX = '_collection'
MIN_NUMBER_OF_ROWS = 6
MAX_NUMBER_OF_ROWS = 12

windowID = 'RenderSetupUtilityWindow'
windowWorkspaceControl = 'WorkspaceControl'
windowVersion = RenderSetupUtility.__version__
windowTitle = 'Render Setup Utility - {}'.format(windowVersion)
windowNewLayerID = 'RenderSetupUtilityNewLayerWin'
windowNewLayerTitle = 'Add New Render Layer'
windowRenameID = 'RenderSetupUtilityRenameWin'
windowRenameTitle = 'Rename Selected'
windowNewShaderID = 'RenderSetupUtilityNewShaderWin'
windowNewShaderTitle = 'Assign Shader'

currentSelection = None
propertyOverridesMode = False
shaderOverrideMode = False
selectedShaderOverride = None
overrideShader = None
shaderUtility = ShaderUtility()


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """

    pass


def resetOptionMenu(inName, inValue, rl=True):
    for item in cmds.optionMenu(inName, q=True, ill=True) or []:
        cmds.deleteUI(item)

    # Add default render layer to menu

    if rl:
        cmds.menuItem(rsUtility.defaultName,
                      label=rsUtility.defaultName, p=inName,
                      enable=True)
    for item in inValue:
        try:
            cmds.menuItem(item, label=item, p=inName)
        except:
            raise RuntimeError('Problem adding menu item.')


def selectOptionMenuItem(inMenuName, inName, rl=True):
    for (index, item) in enumerate(cmds.optionMenu(inMenuName, q=True,
                                   itemListShort=True)):
        okString = re.sub('[^0-9a-zA-Z:]', '_',
                          inName).lstrip('1234567890').lstrip('_')
        if item == okString:
            cmds.optionMenu(inMenuName, e=True, select=index + 1)


def _setTextScrollListVisibleItemNumber():
    q.getQItem('%s_ShaderScrollList' % windowID, QtWidgets.QWidget)
    allItems = cmds.textScrollList(q.fullPath, query=True,
                                   allItems=True)

    if allItems:
        if MIN_NUMBER_OF_ROWS < len(allItems) < MAX_NUMBER_OF_ROWS:
            cmds.textScrollList('%s_ShaderScrollList' % windowID,
                                edit=True, enable=True,
                                numberOfRows=len(allItems))
            cmds.textField('%s_filterShaderList' % windowID, edit=True,
                           enable=True)
            return
        if len(allItems) >= MAX_NUMBER_OF_ROWS:
            cmds.textScrollList('%s_ShaderScrollList' % windowID,
                                edit=True, enable=True,
                                numberOfRows=MAX_NUMBER_OF_ROWS)
            cmds.textField('%s_filterShaderList' % windowID, edit=True,
                           enable=True)
            return
        if len(allItems) <= MIN_NUMBER_OF_ROWS:
            cmds.textScrollList('%s_ShaderScrollList' % windowID,
                                edit=True, enable=True,
                                numberOfRows=MIN_NUMBER_OF_ROWS)
            cmds.textField('%s_filterShaderList' % windowID, edit=True,
                           enable=True)
            return
    else:
        cmds.textScrollList(q.fullPath, edit=True, enable=True,
                            numberOfRows=MIN_NUMBER_OF_ROWS)

        q.getQItem('%s_filterShaderList' % windowID, QtWidgets.QWidget)
        cmds.textField(q.fullPath, edit=True, enable=True)
        return


def _outputTemplate():

    # Output templates

    listItem = []
    menuName = '%s_optionMenu05' % windowID

    for item in renderOutput.OUTPUT_TEMPLATES:
        listItem.append(item)

    resetOptionMenu(menuName, listItem, rl=False)

    imageFilePrefix = cmds.getAttr('%s.imageFilePrefix'
                                   % renderOutput.DEFAULTS_NODE)

    current = [t for t in renderOutput.OUTPUT_TEMPLATES
               if imageFilePrefix == t]
    if current:
        selectOptionMenuItem(menuName, current[0])
        rsRenderOutput.currentTemplate = current[0]

        cmds.button('%s_revealOutputDirectory' % windowID, edit=True,
                    label='')

    # Versions

    lyr = rsUtility.activeLayer.name()
    listItem = []
    menuName = '%s_outputVersionMenu' % windowID
    if cmds.optionMenu('%s_optionMenu05' % windowID, query=True,
                       value=True) == renderOutput.OUTPUT_TEMPLATES[0]:
        cmds.optionMenu('%s_outputVersionMenu' % windowID, edit=True,
                        enable=False)
        cmds.button('%s_incrementOutputVersionButton' % windowID,
                    edit=True, enable=False)
    else:
        cmds.optionMenu('%s_outputVersionMenu' % windowID, edit=True,
                        enable=True)
        cmds.button('%s_incrementOutputVersionButton' % windowID,
                    edit=True, enable=True)
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
    cmds.button('%s_revealOutputDirectory' % windowID, edit=True,
                label='Output path not yet set')
    padding = cmds.getAttr('%s.extensionPadding  '
                           % renderOutput.DEFAULTS_NODE)
    path = rsRenderOutput.pathStr(lyr)
    if path:
        path = path + '_' + '1'.zfill(padding) + '.exr'
        cmds.button('%s_revealOutputDirectory' % windowID, edit=True,
                    label=path)


def getProperyOverridesMode(shaderName):
    """
    Returns the current applied attributes or false.
    """

    appliedAttributes = []
    c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)
    for (index, item) in enumerate(rsUtility.overrideAttributes):
        if c.overrides(item['long']) is not None:
            appliedAttributes.append(c.overrides(item['long'
                    ]).attributeName())
        else:
            appliedAttributes.append('')

    # If any of the attributes present enable propertyOverridesMode.

    if [attr for attr in rsUtility.overrideAttributes if attr['long']
        in appliedAttributes] != []:
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

    q.getQItem('%s_textArnoldPropertyOverridesLabel' % windowID,
               QtWidgets.QLabel)

    def setFalse():
        propertyOverridesMode = False

        q.widget.setStyleSheet('{color: rgb(200,200,200)}')
        q.widget.setText('Apply Arnold Property Overrides')

        for (index, item) in enumerate(rsUtility.overrideAttributes):
            cmds.checkBox('%s_checkbox' % windowID
                          + str(index).zfill(2), edit=True, enable=True)
            cmds.text('%s_text' % windowID + str(index).zfill(2),
                      edit=True, enable=True)

    if sel == []:
        setFalse()
        return False

    # Return false if any of the selected is inactive.

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        c = rsUtility.collection(shaderName.replace(':', '_'),
                                 isQuery=True)

        if shaderUtility.isActive(s) is False:
            setFalse()
            propertyOverridesMode = False
            return False
        mode = getProperyOverridesMode(shaderName)
        if mode is False:
            setFalse()
            propertyOverridesMode = False
            q.widget.setText('No applied arnold overrides found')
            q.widget.setStyleSheet('QLabel {color: rgb(105,105,105); font-weight: normal;}'
                                   )
            return False

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        c = rsUtility.collection(shaderName.replace(':', '_'),
                                 isQuery=True)
        mode = getProperyOverridesMode(shaderName)

        if mode:
            propertyOverridesMode = True

            # Setting checkbox values and ui

            for (index, attr) in enumerate(mode):
                if attr:
                    cmds.checkBox('%s_checkbox' % windowID
                                  + str(index).zfill(2), edit=True,
                                  value=c.getOverrideValue(attr),
                                  enable=True)
                    cmds.text('%s_text' % windowID
                              + str(index).zfill(2), edit=True,
                              enable=True)
                else:

                       # Disabling checkbox if attribute is missing

                    cmds.checkBox('%s_checkbox' % windowID
                                  + str(index).zfill(2), edit=True,
                                  enable=False)
                    cmds.text('%s_text' % windowID
                              + str(index).zfill(2), edit=True,
                              enable=False)

            if len(sel) == 1:
                q.widget.setText('Edit override values:')
            if len(sel) > 1:
                q.widget.setText('Edit override values (multiple):')
            q.widget.setStyleSheet('QLabel {\
                color: rgb(200,200,200);\
                font-weight: bold;\
            }'
                                   )

            return True
        else:
            propertyOverridesMode = False

            # Setting checkbox values and ui

            for (index, attr) in \
                enumerate(rsUtility.overrideAttributes):
                cmds.checkBox('%s_checkbox' % windowID
                              + str(index).zfill(2), edit=True,
                              enable=False)
                cmds.text('%s_text' % windowID + str(index).zfill(2),
                          edit=True, enable=False)

            # Set string

            cmds.text('%s_textArnoldPropertyOverridesLabel' % windowID,
                      edit=True,
                      label='No property overrides in the collection.',
                      enableBackground=False)
            q.widget.setStyleSheet('QLabel {color: rgb(50,50,50)}')

            return False
        break


def _hasOverride(shaderName):
    c = rsUtility.collection(shaderName.replace(':', '_'), isQuery=True)

    if c.hasChildren():
        pass
    else:
        return False

    for child in c.getChildren():
        if child.typeName() == 'collection' \
            and '{0}{1}'.format(shaderName.replace(':', '_'),
                                COLLECTION_SUFFIX) in child.name():
            for o in child.getOverrides():
                if o.typeName() == 'shaderOverride':
                    cnxs = cmds.listConnections(o.name())

                    overrideShader = [cnx for cnx in cnxs
                            if '_collection' not in cnx and '_msg'
                            not in cnx]
                    if overrideShader:
                        pass
                    else:
                        return False

                    shaderName = \
                        shaderUtility.stripSuffix(overrideShader[0])
                    overrideShader = overrideShader[0]
                    if [s for s in SHADER_OVERRIDE_OPTIONS if s['suffix'
                        ] in overrideShader]:
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
        if child.typeName() == 'collection' \
            and '{0}{1}'.format(shaderName.replace(':', '_'),
                                COLLECTION_SUFFIX) in child.name():
            for o in child.getOverrides():
                if o.typeName() == 'shaderOverride':

                    # Getting shader name via connections

                    cnxs = cmds.listConnections(o.name())

                    # Filter collections and 'msg'

                    arr = [cnx for cnx in cnxs if '_collection'
                           not in cnx and '_msg' not in cnx]
                    if arr == []:
                        return False

                    for item in arr:
                        shaderName = shaderUtility.stripSuffix(item)
                        overrideShader = item

                    mode = shaderUtility.getMode(overrideShader)
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
    q.getQItem('%s_shaderOverrideLabel' % windowID, QtWidgets.QLabel)
    shaderOverrideMode = False
    overrideShader = None

    if sel == []:

        # Mode is false

        shaderOverrideMode = False
        selectedShaderOverride = None
        overrideShader = None
        q.widget.setStyleSheet('QLabel {color: rgb(200,200,200)}')
        q.widget.setText('Apply Shader Overrides')
        return False

    # Return false if any of the selected is inactive.

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)

        if shaderUtility.isActive(s) is False:
            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            q.widget.setStyleSheet('QLabel {color: rgb(200,200,200); font-weight: normal;}'
                                   )
            q.widget.setText('Apply Shader Overrides')
            return False

        mode = getShaderOverrideMode(shaderName)
        if mode is None:

            # Doesn't have a shader override

            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            q.widget.setStyleSheet('QLabel {color: rgb(105,105,105); font-weight: normal;}'
                                   )
            q.widget.setText('No shader override in the collection to change'
                             )
            return False

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        mode = getShaderOverrideMode(shaderName)

        if mode:
            shaderOverrideMode = True
            selectedShaderOverride = mode['ui']
            selectOptionMenuItem('%s_optionMenu02' % windowID,
                                 selectedShaderOverride)

            if len(sel) == 1:
                q.widget.setStyleSheet('QLabel {color: rgb(200,200,200); font-weight: bold;}'
                        )
                q.widget.setText('Swap shader override:')
            if len(sel) > 1:
                q.widget.setStyleSheet('QLabel {color: rgb(200,200,200); font-weight: bold;}'
                        )
                q.widget.setText('Swap shader override (multiple):')
            return True
        if mode is False:

            # Doesn't have a shader override

            shaderOverrideMode = False
            selectedShaderOverride = None
            overrideShader = None
            q.widget.setStyleSheet('QLabel {color: rgb(105,105,105); font-weight: normal;}'
                                   )
            q.widget.setText('No shader override in the collection to change'
                             )
            return False
        break


def getListSelection():
    sel = cmds.textScrollList('%s_ShaderScrollList' % windowID,
                              query=True, selectItem=True)
    if sel is None:
        return []
    else:
        return sel


def rsSelectActiveLayer(arg):
    rsUtility.switchLayer(arg, switchLayer=False)
    window.updateUI(updateRenderSetup=False)


def rsSelectVisibleLayer(arg):
    rsUtility.switchLayer(arg, switchLayer=True)
    window.updateUI(updateRenderSetup=True)


def _filterInvalidInput(name):
    data = cmds.textField(name, query=True, text=True)

    inp = re.sub('[^0-9]', '', data)
    if not inp:
        return None

    data = cmds.textField(name, edit=True, text=inp)
    return int(inp)


def getInFrame():
    return cmds.playbackOptions(query=True, animationStartTime=True)


def getOutFrame():
    return cmds.playbackOptions(query=True, animationEndTime=True)


def setInFrame(*args):
    frame = _filterInvalidInput('%s_setInFrame'
                                % RenderSetupUtilityWindow.__name__)

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


def setOutFrame(*args):
    frame = _filterInvalidInput('%s_setOutFrame'
                                % RenderSetupUtilityWindow.__name__)

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


def rsShaderOverridesMenu(arg):
    """
    Shader overrides option menu.
    """

    global shaderOverrideMode
    global selectedShaderOverride
    global overrideShader

    sel = getListSelection()

    if shaderOverrideMode is False:
        return

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        if shaderUtility.isActive(s):
            c = rsUtility.collection(shaderName.replace(':', '_'),
                    isQuery=True)

            if not c.hasChildren():
                continue

            for child in c.getChildren():
                if child.typeName() == 'collection' \
                    and '{0}{1}'.format(shaderName.replace(':', '_'),
                        COLLECTION_SUFFIX) in child.name():

                    for o in child.getOverrides():
                        if o.typeName() != 'shaderOverride':
                            continue

                        newShader = \
                            shaderUtility.duplicateShader(shaderName,
                                choice=arg, isOverride=True)
                        o.setSource(newShader + '.outColor')

                        overrideShader = newShader
                        selectedShaderOverride = arg

    selectedShaderOverride = arg


def rsOutputTemplatesMenu(arg):
    """
    Render Output Size Templates
    """

    r = renderOutput.RESOLUTION_NODE
    choice = [c for c in renderOutput.SIZE_TEMPLATE if arg == c['ui'
              ]][0]
    cmds.setAttr('%s.width' % r, choice['width'])
    cmds.setAttr('%s.height' % r, choice['height'])
    cmds.setAttr('%s.deviceAspectRatio ' % r, float(float(choice['width'
                 ]) / float(choice['height'])))
    cmds.setAttr('%s.aspectLock  ' % r, False)
    cmds.setAttr('%s.pixelAspect   ' % r, float(1))

    c = 'camera'
    if cmds.objExists(c):
        currentAperture = cmds.getAttr('%s.cameraAperture' % c)[0]
        aspect = float(float(choice['width']) / float(choice['height']))
        cmds.setAttr('%s.cameraAperture' % c, currentAperture[0],
                     currentAperture[0] / aspect, type='double2')
        cmds.setAttr('%s.lensSqueezeRatio' % c, float(1.0))
    print '# Output size changed to %s' % choice['ui']


def rsSelectOutputVersion(arg):
    """ Set output version """

    rsRenderOutput.setVersion(arg)
    _updatePathText()


def rsSelectOutputTemplate(arg):
    version = cmds.optionMenu('%s_outputVersionMenu' % windowID,
                              query=True, value=True)
    rsRenderOutput.setTemplate(arg)
    rsRenderOutput.setVersion(version)
    rsRenderOutput.currentTemplate = arg
    _outputTemplate()


def rsSetFPSMenu(arg):
    current = [t for t in renderOutput.TIME_TEMPLATE if arg == t['ui']]
    if current:
        cmds.currentUnit(time=current[0]['name'], updateAnimation=False)
        cmds.playbackOptions(edit=True, playbackSpeed=current[0]['fps'])


def rsShaderGroups(arg):
    text = cmds.textField('%s_filterShaderList' % windowID, edit=True,
                          text=arg)
    window.updateUI(updateRenderSetup=False)


def rsOpenRenderSetupWindow(arg):
    renderSetupUI.createUI()


def rsAddNewLayer(item):
    """
    Window to add new layers.
    """

    WIDTH = WINDOW_WIDTH * (float(4) / 5)
    OFFSET = WINDOW_WIDTH * (float(1) / 5)
    HEIGHT = 75

    if cmds.window(windowNewLayerID, exists=True):
        cmds.deleteUI(windowNewLayerID)

    cmds.window(
        windowNewLayerID,
        sizeable=False,
        title=windowNewLayerTitle,
        iconName=windowNewLayerTitle,
        width=WIDTH,
        height=HEIGHT,
        )

    def rsuNewLayerWindow_button01(arg):
        text = cmds.textField('rsuNewLayerWindow_textField01',
                              query=True, text=True)
        if len(text) > 0:
            rsUtility.layer(text)
        cmds.deleteUI(windowNewLayerID, window=True)
        window.updateUI(updateRenderSetup=True)

    def rsuNewLayerWindow_textField01(arg):
        if len(arg) == 0:
            cmds.button('rsuNewLayerWindow_button01', edit=True,
                        enable=False)
        else:
            cmds.button('rsuNewLayerWindow_button01', edit=True,
                        enable=True)

    cmds.columnLayout(
        'rsuNewLayerWindow_columnLayout01',
        parent=windowNewLayerID,
        columnAlign='center',
        columnAttach=('both', 10),
        columnWidth=WIDTH,
        rowSpacing=1,
        )

    addSeparator('rsuNewLayerWindow_sep01', height=FRAME_MARGIN)
    addText('rsuNewLayerWindow_enterText', 'New layer name:',
            font='boldLabelFont')
    addSeparator('rsuNewLayerWindow_sep02', height=FRAME_MARGIN)
    addTextField('rsuNewLayerWindow_textField01', '',
                 rsuNewLayerWindow_textField01,
                 rsuNewLayerWindow_textField01,
                 rsuNewLayerWindow_textField01)
    cmds.columnLayout('rsuNewLayerWindow_columnLayout02',
                      columnAlign='center', columnAttach=('both', 0),
                      columnWidth=WIDTH - FRAME_MARGIN * 2)
    addButton('rsuNewLayerWindow_button01', 'Create',
              command=rsuNewLayerWindow_button01, enable=False)
    addSeparator('rsuNewLayerWindow_sep03', height=FRAME_MARGIN)
    cmds.showWindow(cmds.window(windowNewLayerID, q=True))

    # Match window position to parent

    q.getQItem(windowNewLayerID, QtWidgets.QWidget)
    globalPos = window.mapToGlobal(window.pos())
    x = globalPos.x() + 28
    y = globalPos.y()
    q.widget.move(x, y)


def rsAddCollection(arg):
    """
    > Add collection based on the selected shader names to the selected render layer.

    Removes objects from any other collections in the layer
    and sets objects used by the shader as the sole selected objects.
    """

    global selectedShaderOverride
    global currentSelection

    DEFAULT_FILTER_TYPE = 2  # shape

    # Disable ui updates

    q.getQItem(windowID, QtWidgets.QWidget)
    q.widget.setUpdatesEnabled(False)

    # Change Override values from UI

    for (index, item) in enumerate(rsUtility.overrideAttributes):
        rsUtility.overrideAttributes[index]['default'] = \
            cmds.checkBox('%s_checkbox' % windowID
                          + str(index).zfill(2), query=True, value=True)

    sel = getListSelection()
    _currentSelection = []

    for s in sel:

        shaderName = shaderUtility.customStringToShaderName(s)
        _currentSelection.append(shaderName)

        rsUtility.activeLayer.collection(shaderName.replace(':', '_'),
                addOverrides=cmds.checkBox('rsArnoldPropertyOverridesCheckBox'
                , query=True, value=True))

        # Add used shapes to the active collection

        rsUtility.activeCollection.setSelection(shaderUtility.data[shaderName]['usedBy'
                ], DEFAULT_FILTER_TYPE)

        # Remove objects from other collections:

        cl = rsUtility.activeLayer.getCollections()
        for c in cl:
            if c.name() != rsUtility.activeCollection.name():
                if c.typeName() == 'collection':
                    c.getSelector().staticSelection.remove(shaderUtility.data[shaderName]['usedBy'
                            ])

        if _hasOverride(shaderName) is False:

            # Shader override

            shaderOverrideCB = cmds.checkBox('%s_shaderOverrideCheckbox'
                     % windowID, query=True, value=True)

            if shaderOverrideCB:
                choice = cmds.optionMenu('%s_optionMenu02' % windowID,
                        query=True, value=True)

                # Create the shader override shader

                overrideShader = \
                    shaderUtility.duplicateShader(shaderName,
                        choice=choice, applyOp=shaderOverrideCB)

                o = rsUtility.addShaderOverride()
                o.setSource(overrideShader + '.outColor')

                selectedShaderOverride = choice

    currentSelection = _currentSelection
    window.updateUI(updateRenderSetup=True)
    q.widget.setUpdatesEnabled(True)


def rsRemoveCollection(arg):
    """ < Remove colllections """

    # Disable ui updates

    q.getQItem(windowID, QtWidgets.QWidget)
    q.widget.setUpdatesEnabled(False)

    sel = getListSelection()
    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        rsUtility.activeLayer.removeCollection(shaderName.replace(':',
                '_'))

    window.updateUI(updateRenderSetup=True)
    q.widget.setUpdatesEnabled(True)


def rsRenameShader(arg):
    """
    Rename Shader
    """

    sel = getListSelection()
    if sel is None or sel is []:
        return None
    if len(sel) != 1:
        return None

    WIDTH = WINDOW_WIDTH * (float(4) / 5)
    OFFSET = WINDOW_WIDTH * (float(1) / 5)
    HEIGHT = 75

    if cmds.window(windowRenameID, exists=True):
        cmds.deleteUI(windowRenameID)

    cmds.window(
        windowRenameID,
        sizeable=False,
        title=windowRenameTitle,
        iconName=windowRenameTitle,
        width=WIDTH,
        height=HEIGHT,
        )

    def rsuRenameWindow_button01(arg):
        global currentSelection

        text = cmds.textField('rsuRenameWindow_textField01',
                              query=True, text=True)
        sel = getListSelection()
        if len(text) > 0:
            shaderName = shaderUtility.customStringToShaderName(sel[0])
            items = cmds.ls(shaderName + '*', long=False)
            for item in items:
                if cmds.objExists(item):
                    cmds.rename(item, item.replace(shaderName, text))

        sel = getListSelection()
        shaderName = shaderUtility.customStringToShaderName(sel[0])
        _currentSelection = []
        currentSelection = _currentSelection.append(shaderName)

        window.updateUI()
        cmds.deleteUI(windowRenameID, window=True)

    def rsuRenameWindow_textField01(arg):
        try:  # rsuRenameWindow_button01 does not exist the first time this is called
            if len(arg) == 0:
                cmds.button('rsuRenameWindow_button01', edit=True,
                            enable=False)
            else:
                if arg \
                    in shaderUtility.getShaderList(excludeOverrides=False,
                        excludeUnused=False):
                    cmds.button('rsuRenameWindow_button01', edit=True,
                                enable=False,
                                label='Name exists already')
                else:
                    cmds.button('rsuRenameWindow_button01', edit=True,
                                enable=True, label='Rename')
        except:
            pass

    cmds.columnLayout('rsuRenameWindow_columnLayout01',
                      columnAlign='center', columnAttach=('both', 10),
                      columnWidth=WIDTH, rowSpacing=1)
    addSeparator('rsuRenameWindow_sep01', height=FRAME_MARGIN)
    addText('rsuRenameWindow_enterText', 'Enter New Name:',
            font='boldLabelFont')
    addSeparator('rsuRenameWindow_sep02', height=FRAME_MARGIN)

    addTextField('rsuRenameWindow_textField01', '',
                 rsuRenameWindow_textField01,
                 rsuRenameWindow_textField01,
                 rsuRenameWindow_textField01)

    sel = getListSelection()
    shaderName = shaderUtility.customStringToShaderName(sel[0])
    text = cmds.textField('rsuRenameWindow_textField01', edit=True,
                          text=shaderName)

    cmds.columnLayout('rsuRenameWindow_columnLayout02',
                      columnAlign='center', columnAttach=('both', 0),
                      columnWidth=WIDTH - FRAME_MARGIN * 2)
    addButton('rsuRenameWindow_button01', 'Rename',
              command=rsuRenameWindow_button01, enable=False)
    addSeparator('rsuRenameWindow_sep03', height=FRAME_MARGIN)
    cmds.showWindow(cmds.window(windowRenameID, q=True))

    q.getQItem(windowRenameID, QtWidgets.QWidget)
    globalPos = window.mapToGlobal(window.pos())
    x = globalPos.x() + 28
    y = globalPos.y()
    q.widget.move(x, y)


def rsSelectShapes(*args):
    """
    Select shape transforms
    """

    parents = []
    sel = getListSelection()
    for s in sel:
        n = shaderUtility.customStringToShaderName(s)
        usedBy = shaderUtility.data[n]['usedBy']
        for u in usedBy:
            parent = cmds.listRelatives(u, allParents=True,
                    path=True)[0]
            parents.append(parent)
    cmds.select(parents)


def rsRefreshUI(*args):
    """ Refresh button """

    window.updateUI()


def duplicateShader(*args):
    sel = getListSelection()
    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        duplicate = shaderUtility.duplicateShader(shaderName,
                isOverride=False)
        shaderUtility.transferShaderAttributes(shaderName, duplicate)


def editTexture(arg=None):
    """ AutoConnect - Edit Textures """

    # Check if ac found a valid Photoshop path:

    if autoConnect.AutoConnect.PHOTOSHOP_PATH is None:
        raise WindowsError('Sorry, couldn\'t find an Adobe Photoshop installation in the Windows Registry.'
                           )

    ac = autoConnect.AutoConnect()

    sel = getListSelection()
    if sel == []:
        print '# Edit Texture: No shader selected #'
        return

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        if not next((k for k in ac.DATA.keys() if shaderName == k),
                    None):
            print '# No texture file found to edit for the specified shader. #'
            raise RuntimeError('There doesn\'t seem to be an AutoConnect setup for the shader.'
                               )

        np = path.normpath(ac.DATA[shaderName]['psdPath'])
        print '# Edit Texture: Opening texture file for shader \'%s\': %s' \
            % (shaderName, np)
        cmd = '"%s" "%s"' % (path.normpath(ac.PHOTOSHOP_PATH), np)
        process = QProcess()
        process.startDetached(cmd)

        break


def updateConnections(args=None):
    """ AutoConnect - Update connections """

    sel = getListSelection()
    if sel == []:
        print '# Update Connections: No shader selected #'
        return

    ac = autoConnect.AutoConnect()

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        print '# Updating \'%s\' shader connections #' % shaderName
        ac.doIt(shaderName)


def rsIncrementOutputVersion():
    """
    +1 button. Increments the version number of the output.
    """

    lyr = rsUtility.activeLayer.name()
    versions = rsRenderOutput.getVersions(lyr)

    if versions:
        search = re.search('[0-9]{3}', versions[-1])
        if search:
            newVersion = 'v{0}'.format(str(int(search.group(0))
                    + 1).zfill(3))
            rsRenderOutput.addVersionDir(lyr, newVersion)
            rsRenderOutput.setVersion(newVersion)
            _outputTemplate()

    _updatePathText()


def rsMakeComp():
    """
    AutoConnect - Make Comp

    Creates a temporary placeholder exr sequence for the current render layer.
    Also export and imports the camera called 'camera'.

    If the current render setup layer name contains 'layout' then the placeholder sequence
    will be substituted with a playblast of 'camera'.
    """

    pathControlSelection = cmds.optionMenu('%s_optionMenu05'
            % windowID, query=True, value=True)
    if cmds.objExists('camera') is False:
        print '# Couldn\'t find \'camera\' #'
        raise RuntimeError('Couldn\'t find the camera. Make sure the main camera is called \'camera\''
                           )

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

    sn = cmds.file(query=True, sn=True, shortName=True)
    if sn:

        # removes the versioning // Studio AKA specific setting.

        SCENE_NAME = (sn.split('.')[0])[:-4]
    else:
        SCENE_NAME = 'untitled_maya_scene'

    currentWidth = si.currentWidth
    currentHeight = si.currentHeight
    OUTPUT_OPTION = [w for w in renderOutput.SIZE_TEMPLATE
                     if currentWidth == w['width'] and currentHeight
                     == w['height']]
    TEMPLATE = None
    IMAGE_PATHS = []
    FOOTAGE_NAMES = []
    MAYA_CAMERA = None

    # Check output templates

    if OUTPUT_OPTION == []:
        raise RuntimeError('The current output size is not one of the defined templates. This is unsupported.\n\
            To continue, select one of the templated output formats.'
                           )
    TEMPLATE = OUTPUT_OPTION[0]['suffix']

    if pathControlSelection == renderOutput.OUTPUT_TEMPLATES[0]:
        print '# Output path not yet set #'
        raise RuntimeError('Path template is not set. To continue, select one of the output path templates.'
                           )

    LAYER_NAME = renderSetup.instance().activeLayer.name()
    VERSION = cmds.optionMenu('%s_outputVersionMenu' % windowID,
                              query=True, value=True)

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
            BASE_PATH = rsRenderOutput.pathStr(LAYER_NAME,
                    long=True).replace('<AOV>', aov)

        if BASE_PATH is None:
            raise RuntimeError('Couldn\'t get path from the render output path tokens.'
                               )

        # Make folders

        k = BASE_PATH.rfind('\\')
        root = BASE_PATH[:k]

        if os.path.isdir(root) is False:
            os.makedirs(root)

        # Decode the exr template file

        decoded = base64.b64decode(templates.EXR_TEMPLATES[TEMPLATE])

        if 'layout' in LAYER_NAME:
            p = '%s.%s.%s' % (BASE_PATH,
                              str(int(START_FRAME)).zfill(4), 'jpg')
            IMAGE_PATH = os.path.normpath(p)
        else:
            p = '%s_%s.%s' % (BASE_PATH,
                              str(int(START_FRAME)).zfill(4), EXTENSION)
            IMAGE_PATH = os.path.normpath(p)

        confirm = 'Overwrite'

        if os.path.isfile(IMAGE_PATH) is True:
            confirm = cmds.confirmDialog(
                title='Warning',
                message='''\
%s - %s: Render images already exists at the current location.

\
If you choose \'Overwrite\', they will be replaced with a blank placeholder sequence.
\
Otherwise click \'Import Existing\' to import the existing sequence (recommended).

\
Image Path:
%s\
'''
                    % (LAYER_NAME, aov, IMAGE_PATH),
                button=['Import Existing', 'Overwrite'],
                defaultButton='Import Existing',
                cancelButton='Import Existing',
                dismissString='Import Existing',
                )

        if confirm == 'Overwrite':
            if 'layout' in LAYER_NAME:
                p = '%s' % BASE_PATH
                IMAGE_PATH = os.path.normpath(p)

                multiSample = \
                    cmds.getAttr('hardwareRenderingGlobals.multiSampleEnable'
                                 )
                ssao = \
                    cmds.getAttr('hardwareRenderingGlobals.ssaoEnable')

                window = autoConnect.captureWindow(int(currentWidth)
                        * 0.50, int(currentHeight) * 0.50 + 30)

                # Tying to force Maya to retain this setting...
                # Set image format to jpg

                cmds.setAttr('%s.imageFormat'
                             % renderOutput.DEFAULTS_NODE, 8)

                # Make pers non-renderable

                cmds.setAttr('perspShape.renderable', 0)

                # Make camera renderable, if exists.

                cmds.setAttr('cameraShape.renderable', 1)

                cmds.playblast(  # compression=compression,
                    format='image',
                    percent=int(100),
                    viewer=False,
                    startTime=int(START_FRAME),
                    endTime=int(END_FRAME),
                    showOrnaments=True,
                    forceOverwrite=True,
                    filename=str(IMAGE_PATH),
                    widthHeight=[int(currentWidth),
                                 int(currentHeight)],
                    rawFrameNumbers=True,
                    framePadding=int(4),
                    )

                cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable'
                             , multiSample)
                cmds.setAttr('hardwareRenderingGlobals.ssaoEnable',
                             ssao)

                window.close()

                p = '%s.%s.%s' % (BASE_PATH,
                                  str(int(START_FRAME)).zfill(4), 'jpg')
                IMAGE_PATH = os.path.normpath(p)
            else:
                for (index, n) in enumerate(DURATION):
                    p = '%s_%s.%s' % (BASE_PATH, str(n).zfill(4),
                            EXTENSION)
                    IMAGE_PATH = os.path.normpath(p)
                    try:
                        imageFile = open(IMAGE_PATH, 'w')
                        imageFile.write(decoded)
                        imageFile.close()
                    except:
                        print '# Couldn\'t create temp image files.'

        IMAGE_PATH = os.path.normpath(p)
        IMAGE_PATHS.append(str(IMAGE_PATH))
        footageName = BASE_PATH[k + 1:]
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

    # ############################################################
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
    scriptPath = os.path.normpath(os.path.join(tempfile.gettempdir(),
                                  'aeCommand.jsx'))

    # #############################################
    # Script file

    script = aeCommand.script
    AE_SCRIPT = script.replace('<Name>',
                               str(SCENE_NAME)).replace('<Width>',
            str(currentWidth)).replace('<Height>',
            str(currentHeight)).replace('<Pixel_Aspect>',
            str(1)).replace('<Duration>', str(float(len(DURATION))
                            / float(FRAME_RATE))).replace('<Frame_Rate>'
            , str(float(FRAME_RATE))).replace('<Image_Paths>',
            str(IMAGE_PATHS)).replace('<Footage_Names>',
            str(FOOTAGE_NAMES)).replace('<Maya_Camera>',
            MAYA_CAMERA.replace('\\', '\\\\'))

    # #############################################

    AE_SCRIPT_FILE = open(scriptPath, 'w')
    AE_SCRIPT_FILE.write(str(AE_SCRIPT))
    AE_SCRIPT_FILE.close()

    try:
        cmd = '"%s" -r "%s"' % (ac.AFTER_EFFECTS_PATH, scriptPath)
        process = QProcess()
        process.startDetached(cmd)
    except KeyError:
        print "# There doesn't seem to be an AutoConnect setup for that shader."


def rsRevealOutputDirectory(*args):

    # IMAGES_ROOT = 'images' #maya default

    IMAGES_ROOT = 'renders'  # glassworks pipe

    val = cmds.button('%s_revealOutputDirectory' % windowID,
                      query=True, label=True)
    if val == 'Output path not yet set':
        print '# Output path not yet set - Unable to open directory'
        return
    else:
        cmd = None
        workspace = cmds.workspace(query=True, rootDirectory=True)
        if workspace:
            p = os.path.join(workspace, IMAGES_ROOT, val)
            p = os.path.normpath(p)
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

            if cmd:
                process = QProcess()
                process.startDetached(cmd)
            print '# Unable to get reveal directory - Folder doesn\'t exist'
            print '# Parent: {0}'.format(parent)
        else:
            raise RuntimeError('File has not been saved. Unable to get path.'
                               )


def uvSnapshot(arg=None):
    """
    AutoConnect - Creates a UV Snapshot and tries to apply it to the assigned Photoshop document.
    """

    FILE_NAME = 'uv.jpg'
    RESOLUTION = 4096

    sel = getListSelection()
    ac = autoConnect.AutoConnect()

    if ac.PHOTOSHOP_PATH is None:
        raise WindowsError('Couldn\'t find Adobe Photoshop.')

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        if [f for f in ac.DATA.keys() if shaderName == f] == []:
            print '# Shader doesn\'t have an AutoConnect setup.'
            continue

        # Launch photoshop process

        editTexture()

        usedBy = shaderUtility.data[shaderName]['usedBy']
        parents = []
        for u in usedBy:
            parent = cmds.listRelatives(u, allParents=True,
                    path=True)[0]
            parents.append(parent)
        cmds.select(parents)

        p = path.normpath(path.join(ac.workspace, ac.sourceImages,
                          shaderName))
        if os.path.isdir(p) is not True:
            os.mkdir(p)
        path.normpath(path.join(p, FILE_NAME))
        cmds.uvSnapshot(
            name=path.normpath(path.join(p, FILE_NAME)),
            overwrite=True,
            antiAliased=True,
            fileFormat='jpg',
            xResolution=RESOLUTION,
            yResolution=RESOLUTION,
            )

        # Let's call Photoshop

        script = psCommand.script
        PS_SCRIPT = script.replace('<UV_Image_Path>',
                                   path.normpath(path.join(p,
                                   FILE_NAME)).replace('\\', '\\\\'
                                   )).replace('<Texture_PSD_Name>',
                '%s.psd' % shaderName)

        tempDir = tempfile.gettempdir()
        scriptFile = 'psScript.jsx'

        p = path.join(tempDir, scriptFile)
        f = open(p, 'w')
        f.write(PS_SCRIPT)
        f.close()

        cmd = '"%s" "%s"' % (path.normpath(ac.PHOTOSHOP_PATH),
                             path.normpath(p))
        process = QProcess()
        process.startDetached(cmd)


def rsFilterShaderList_off(arg):
    pass


def rsShaderScrollList_doubleClick():
    global shaderOverrideMode
    global selectedShaderOverride

    sel = getListSelection()
    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        overrideShader = [f for f in SHADER_OVERRIDE_OPTIONS if f['ui']
                          == selectedShaderOverride]
        if overrideShader == []:
            cmds.select(shaderName, replace=True)
            cmds.HypershadeWindow()
            cmds.evalDeferred('mel.eval(\'hyperShadePanelGraphCommand("hyperShadePanel1","showUpAndDownstream");\')'
                              )
            break
        else:
            for item in overrideShader:
                overrideShaderName = '%s%s_%s' % (shaderName,
                        item['suffix'], item['type'])
                if cmds.objExists(overrideShaderName) is True:
                    cmds.select(overrideShaderName, replace=True)
                    cmds.HypershadeWindow()
                    cmds.evalDeferred('mel.eval(\'hyperShadePanelGraphCommand("hyperShadePanel1","showUpAndDownstream");\')'
                            )
                break


def rsShaderScrollList_deleteKey():
    cmds.select(clear=True)
    sel = getListSelection()
    if sel is not None:
        for s in sel:
            shaderName = shaderUtility.customStringToShaderName(s)
            cmds.select(shaderName, add=True)


def rsShaderScrollList_onSelect(*args):
    """
    Function called when the a list item is selected
    Update setModes and current selection
    """

    global currentSelection

    sel = getListSelection()
    _currentSelection = []

    for s in sel:
        shaderName = shaderUtility.customStringToShaderName(s)
        if shaderUtility.data[shaderName]['shader']:
            try:
                window.gwCustomRenamer.setOptionMenu1(value=shaderName.split('_'
                        )[0])
                window.gwCustomRenamer.setOptionMenu2(value=shaderName.split('_'
                        )[1])
            except:
                pass

        _currentSelection.append(shaderName)

    setPropertyOverridesMode()
    setShaderOverrideMode()
    currentSelection = _currentSelection


def postMenuCommand(*args):
    sel = getListSelection()
    if sel == []:
        for item in cmds.popupMenu(args[0], query=True, itemArray=True):
            cmds.menuItem(item, edit=True, enable=False)
    if sel != []:
        for item in cmds.popupMenu(args[0], query=True, itemArray=True):
            cmds.menuItem(item, edit=True, enable=True)


def rsArnoldPropertyOverridesCheckBox(arg):
    cmds.columnLayout('%s_columnLayout02' % windowID, edit=True,
                      visible=arg)


def setOverrideValue(arg, index=None):
    global propertyOverridesMode
    setPropertyOverridesMode()

    sel = getListSelection()

    for s in sel:
        if propertyOverridesMode is True:
            shaderName = shaderUtility.customStringToShaderName(s)
            c = rsUtility.activeLayer.collection(shaderName.replace(':'
                    , '_'), isQuery=True)
            c.setOverrideValue(rsUtility.overrideAttributes[index]['long'
                               ], arg)

    rsUtility.overrideAttributes[index]['default'] = arg

    def update():
        if propertyOverridesMode is True:
            window.updateUI(updateRenderSetup=True)
        else:
            window.updateUI(updateRenderSetup=False)

    cmds.evalDeferred(update)


def rsShaderOverrideCheckbox(arg):
    """Shader override toggle"""

    cmds.columnLayout('%s_columnLayout03' % windowID, edit=True,
                      visible=arg)


# UI Functions

def addScrollLayout(
    inTitle,
    parent,
    enable=True,
    visible=True,
    ):
    cmds.scrollLayout(
        inTitle,
        parent=parent,
        verticalScrollBarAlwaysVisible=False,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        horizontalScrollBarThickness=SCROLLBAR_THICKNESS,
        verticalScrollBarThickness=SCROLLBAR_THICKNESS,
        enable=enable,
        visible=visible,
        )


def addFrameLayout(
    inName,
    label,
    enable=True,
    marginWidth=FRAME_MARGIN,
    marginHeight=FRAME_MARGIN,
    collapsable=False,
    collapse=False,
    font='plainLabelFont',
    borderVisible=False,
    visible=True,
    labelVisible=True,
    ):
    cmds.frameLayout(
        inName,
        label=label,
        collapsable=collapsable,
        collapse=collapse,
        font=font,
        borderVisible=borderVisible,
        backgroundColor=FRAME_BACKGROUND,
        marginWidth=marginWidth,
        marginHeight=marginHeight,
        labelAlign='center',
        labelVisible=labelVisible,
        labelIndent=0,
        )


def addRowLayout(
    inName,
    numberOfColumns,
    columnAlign1='',
    columnAlign2=('', ''),
    columnAlign3=('', '', ''),
    columnAlign4=('', '', '', ''),
    columnAlign5=('', '', '', '', ''),
    columnAlign6=(
        '',
        '',
        '',
        '',
        '',
        '',
        ),
    columnAttach1='',
    columnAttach2=('', ''),
    columnAttach3=('', '', ''),
    columnAttach4=('', '', '', ''),
    columnAttach5=('', '', '', '', ''),
    columnAttach6=(
        '',
        '',
        '',
        '',
        '',
        '',
        ),
    columnWidth1=0,
    columnWidth2=(0, 0),
    columnWidth3=(0, 0, 0),
    columnWidth4=(0, 0, 0, 0),
    columnWidth5=(0, 0, 0, 0, 0),
    columnWidth6=(
        0,
        0,
        0,
        0,
        0,
        0,
        ),
    columnOffset1=0,
    columnOffset2=(0, 0),
    columnOffset3=(0, 0, 0),
    columnOffset4=(0, 0, 0, 0),
    columnOffset5=(0, 0, 0, 0, 0),
    columnOffset6=(
        0,
        0,
        0,
        0,
        0,
        0,
        ),
    enable=True,
    visible=True,
    ):
    cmds.rowLayout(
        inName,
        numberOfColumns=numberOfColumns,
        columnAlign1=columnAlign1,
        columnAlign2=columnAlign2,
        columnAlign3=columnAlign3,
        columnAlign4=columnAlign4,
        columnAlign5=columnAlign5,
        columnAlign6=columnAlign6,
        columnAttach1=columnAttach1,
        columnAttach2=columnAttach2,
        columnAttach3=columnAttach3,
        columnAttach4=columnAttach4,
        columnAttach5=columnAttach5,
        columnAttach6=columnAttach6,
        columnWidth1=columnWidth1,
        columnWidth2=columnWidth2,
        columnWidth3=columnWidth3,
        columnWidth4=columnWidth4,
        columnWidth5=columnWidth5,
        columnWidth6=columnWidth6,
        columnOffset1=columnOffset1,
        columnOffset2=columnOffset2,
        columnOffset3=columnOffset3,
        columnOffset4=columnOffset4,
        columnOffset5=columnOffset5,
        columnOffset6=columnOffset6,
        enable=enable,
        visible=visible,
        )


def addOptionMenu(
    inName,
    label,
    inArr,
    changeCommand,
    enable=True,
    visible=True,
    size=(50, 22),
    ):
    cmds.optionMenu(  # width = size[0],
        inName,
        label=label,
        changeCommand=changeCommand,
        height=size[1],
        enable=enable,
        visible=visible,
        alwaysCallChangeCommand=True,
        )
    for a in inArr:
        cmds.menuItem(label=a)


def addButton(
    inTitle,
    label,
    command,
    size=(50, 21),
    image=None,
    enable=True,
    visible=True,
    ):
    if image is None:
        cmds.button(
            inTitle,
            label=label,
            command=command,
            width=size[0],
            height=size[1],
            enable=enable,
            visible=visible,
            )
    else:
        cmds.symbolButton(
            inTitle,
            command=command,
            width=size[0],
            height=size[1],
            image=image,
            enable=enable,
            visible=visible,
            )


def addTextField(
    inTitle,
    placeholderText,
    enterCommand,
    textChangedCommand,
    changeCommand,
    enable=True,
    visible=True,
    ):
    cmds.textField(
        inTitle,
        placeholderText=placeholderText,
        enterCommand=enterCommand,
        textChangedCommand=textChangedCommand,
        editable=True,
        enable=enable,
        visible=visible,
        )


def addText(inTitle, label, font='plainLabelFont'):
    cmds.text(inTitle, label=label, font=font)


def addSeparator(
    inTitle,
    height=21,
    style='none',
    horizontal=True,
    enable=True,
    visible=True,
    ):
    cmds.separator(
        inTitle,
        height=height,
        style=style,
        horizontal=horizontal,
        enable=enable,
        visible=visible,
        )


def addTextScrollList(
    inTitle,
    inArr,
    doubleClickCommand,
    selectCommand,
    deleteKeyCommand,
    enable=True,
    visible=True,
    ):
    cmds.textScrollList(
        inTitle,
        append=inArr,
        numberOfItems=len(inArr),
        numberOfRows=MIN_NUMBER_OF_ROWS,
        doubleClickCommand=doubleClickCommand,
        selectCommand=selectCommand,
        deleteKeyCommand=deleteKeyCommand,
        allowMultiSelection=True,
        enable=enable,
        visible=visible,
        )


def addCheckBox(
    inTitle,
    label,
    offCommand,
    onCommand,
    value=False,
    enable=True,
    visible=True,
    ):
    cmds.checkBox(
        inTitle,
        label=label,
        offCommand=offCommand,
        onCommand=onCommand,
        value=value,
        enable=enable,
        visible=visible,
        )


def addCheckboxes(parent):

    for (index, item) in enumerate(rsUtility.overrideAttributes):

        cmds.setParent(parent)
        addRowLayout(
            '%s_rowLayout' % windowID + str(index).zfill(2),
            2,
            columnOffset2=(20, 0),
            columnAlign2=('left', 'left'),
            columnAttach2=('left', 'right'),
            columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.85,
                          (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.15
                          - 1.0),
            )

        addText('%s_text' % windowID + str(index).zfill(2), item['nice'
                ] + util.addChars(' ', 100))
        command = functools.partial(setOverrideValue, index=index)
        cmds.checkBox('%s_checkbox' % windowID + str(index).zfill(2),
                      label='', changeCommand=command,
                      value=item['default'])


class QGet(QtCore.QObject):

    def __init__(self, parent=None):
        super(QGet, self).__init__(parent=parent)

        ptr = OpenMayaUI.MQtUtil.mainWindow()
        self.mayaMainWindow = shiboken2.wrapInstance(long(ptr),
                QtWidgets.QMainWindow)

        self.QRenderView = None
        self.QRenderViewControl = None
        self.widget = None
        self.fullPath = None
        self.layout = None

    def _setFullPath(self):
        try:
            layout = self.widget.layout()
            if layout:
                ptr = long(shiboken2.getCppPointer(layout)[0])
            else:
                ptr = long(shiboken2.getCppPointer(self.widget)[0])
            self.fullPath = OpenMayaUI.MQtUtil.fullName(ptr)
        except:
            self.fullPath = None
        return self.fullPath

    def getQItem(self, string, QType):
        ptr = OpenMayaUI.MQtUtil.findControl(string)
        if ptr is None:
            self.widget = None
            self.layout = None
        else:
            self.widget = shiboken2.wrapInstance(long(ptr), QType)
            self.layout = self.widget.layout()

        self._setFullPath()
        return self.widget

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
            for obj in QtWidgets.QApplication.allWidgets():
                if type(obj) is QtWidgets.QMainWindow:
                    if obj.windowTitle() == 'Arnold Render View':
                        self.QRenderView = obj
                        break
            for obj in QtWidgets.QApplication.allWidgets():
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
        for obj in QtWidgets.QApplication.allWidgets():
            if type(obj) is QtWidgets.QWidget:
                if obj.windowTitle() == string:
                    self.widget = obj
        self._setFullPath()
        return self.widget

    def getByObjectName(self, string):
        for obj in QtWidgets.QApplication.allWidgets():
            if type(obj) is QtWidgets.QWidget:
                if obj.objectName() == string:
                    self.widget = obj
        self._setFullPath()
        return self.widget

    def getControlByName(self, string):
        ptr = OpenMayaUI.MQtUtil.findControl(string)
        if ptr is None:
            self.widget = None
        else:
            self.widget = shiboken2.wrapInstance(long(ptr), QType)

        self._setFullPath()
        return self.widget


q = QGet()


class CustomRenamer(object):

    """
        The class enforces a naming convention when creating shaders and provides easy access
        to assign shaders to the current mesh selection.

        It also rename objects based on their shader assignment.
        If no selection is present, renames shaders and their associated
        texture files (using the autoConnect rename() function)
    """

    OBJ_TYPES = {
        'transform': '_t',
        'mesh': 'Shape',
        'nurbsSurface': 'Shape',
        'nurbsCurve': 'Crv',
        'bezierCurve': 'Crv',
        'locator': 'Loc',
        }

    def __init__(self, newName='untitled'):

        self.windowID = '%sWindow' % windowID
        self.windowTitle = '%sWindow' % windowID

        self.newName = newName
        self.shaderType = SHADER_TYPES[0]

        self.optionMenu1Sel = None
        self.optionMenu2Sel = None
        self.optionMenu3Sel = None

        self.textField1Sel = ''
        self.textField2Sel = ''
        self.textField3Sel = ''

        self.renderSetupUtilityWindow = q.getQItem(windowID,
                QtWidgets.QWidget)

    def _filter(self, lst):
        """ Returns a filtered list accepting only the specified object types.
        The resulting list is reverse sorted, to avoid missing object names when renaming."""

        lst = list(set(lst))  # removes duplicate items
        if lst is None:
            return []
        arr = []
        for item in lst:
            for typ in [str(g) for g in self.__class__.OBJ_TYPES]:
                if cmds.objectType(item) == typ:
                    arr.append(item)

        arr.sort(key=lambda x: x.count('|'))
        return arr[::-1]  # reverse list

    def setName(self, newName):
        self.newName = newName
        return self.newName

    def _children(self, name):
        children = cmds.listRelatives(name, fullPath=True,
                allDescendents=True)
        if children:
            return self._filter(children)
        else:
            return []

    def doIt(self):
        """ perform rename """

        def _getAssignedShader(name):
            dct = shaderUtility.data
            for key in dct.keys():
                for item in dct[key]['usedBy']:
                    if child in item:
                        return key

        sel = self._filter([cmds.listRelatives(f, parent=True)[0]
                           for f in cmds.ls(selection=True)
                           if cmds.objectType(f) in ['mesh',
                           'nurbsSurface']] + [f for f in
                           cmds.ls(selection=True)
                           if cmds.objectType(f) in ['transform']])

        if not sel:
            return []
        if not self.newName:
            return []

        for name in sel:
            suffix = [self.__class__.OBJ_TYPES[f] for f in
                      self.__class__.OBJ_TYPES if f
                      == cmds.objectType(name)][0]
            cmds.rename(name, '%s%s#' % (self.newName, suffix),
                        ignoreShape=False)

        self.updateUI(updateWindow=True)

    def setOptionMenu1(self, value=''):
        cmds.optionMenu('%s_optionMenu01' % self.windowID, query=True,
                        value=True)

        items = cmds.optionMenu('%s_optionMenu01' % self.windowID,
                                query=True, itemListShort=True)
        if items:
            for (index, item) in enumerate(items):
                label = cmds.menuItem(item, query=True, label=True)
                if label == value:
                    cmds.optionMenu('%s_optionMenu01' % self.windowID,
                                    edit=True, select=index + 1)
        self.optionMenu01_changeCommand()

    def setOptionMenu2(self, value=''):
        cmds.optionMenu('%s_optionMenu02' % self.windowID, query=True,
                        value=True)

        items = cmds.optionMenu('%s_optionMenu02' % self.windowID,
                                query=True, itemListShort=True)
        if items:
            for (index, item) in enumerate(items):
                label = cmds.menuItem(item, query=True, label=True)
                if label == value:
                    cmds.optionMenu('%s_optionMenu02' % self.windowID,
                                    edit=True, select=index + 1)
        self.optionMenu02_changeCommand()

    def optionMenu01_changeCommand(self, *args):

        # Select group:

        optionMenu01Value = cmds.optionMenu('%s_optionMenu01'
                % self.windowID, query=True, value=True)
        textField = cmds.textField('%s_textField01' % self.windowID,
                                   edit=True, text=optionMenu01Value)

        # Populate children list:

        if optionMenu01Value is None:
            return
        optionMenu02Value = cmds.optionMenu('%s_optionMenu02'
                % self.windowID, query=True, value=True)
        if optionMenu02Value is None:
            for item in \
                util.natsort(shaderUtility.getShaderGroups()[optionMenu01Value]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'
                              % self.windowID)
        else:
            for item in cmds.optionMenu('%s_optionMenu02'
                    % self.windowID, query=True, itemListLong=True):
                cmds.deleteUI(item)
            for item in \
                util.natsort(shaderUtility.getShaderGroups()[optionMenu01Value]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'
                              % self.windowID)

        # Select group:

        optionMenu02Value = cmds.optionMenu('%s_optionMenu02'
                % self.windowID, query=True, value=True)
        textField = cmds.textField('%s_textField02' % self.windowID,
                                   edit=True, text=optionMenu02Value)

    def optionMenu02_changeCommand(self, *args):
        value = cmds.optionMenu('%s_optionMenu02' % self.windowID,
                                query=True, value=True)
        cmds.textField('%s_textField02' % self.windowID, edit=True,
                       text=value)

    def optionMenu03_changeCommand(self, *args):
        value = cmds.optionMenu('%s_optionMenu03' % self.windowID,
                                query=True, value=True)
        self.shaderType = value

    def makeNameString(self, *args):
        textField01 = cmds.textField('%s_textField01' % self.windowID,
                query=True, text=True)
        textField02 = cmds.textField('%s_textField02' % self.windowID,
                query=True, text=True)
        textField03 = cmds.textField('%s_textField03' % self.windowID,
                query=True, text=True)

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

        WIDTH = WINDOW_WIDTH - FRAME_MARGIN * 2

        if cmds.workspaceControl(self.windowID, exists=True):
            cmds.deleteUI(self.windowID)

        sel = cmds.ls(selection=True)
        placeholderText = ''

        backgroundColor = [0.28] * 3
        height = 22

        cmds.columnLayout(
            '%s_columnLayout01' % self.windowID,
            parent='%s_frameLayout05' % 'RenderSetupUtilityWindow',
            columnAlign='left',
            columnAttach=('left', 0),
            adjustableColumn=False,
            rowSpacing=0,
            backgroundColor=backgroundColor,
            )

        # height=24

        cmds.separator(parent='%s_columnLayout01' % self.windowID,
                       style='none', height=6)

        if cmds.ls(selection=True):
            cmds.ls(selection=True)[0]
        else:
            placeholder = 'newName'

        # row2

        cmds.rowLayout(
            '%s_rowLayoutActiveRenderLayer' % self.windowID,
            parent='%s_columnLayout01' % self.windowID,
            numberOfColumns=3,
            columnAlign3=('left', 'left', 'right'),
            columnAttach3=('both', 'both', 'both'),
            columnWidth3=(WIDTH / 3, WIDTH / 3, WIDTH / 3),
            enableBackground=True,
            backgroundColor=backgroundColor,
            )
        cmds.textField(
            '%s_textField01' % self.windowID,
            placeholderText='Groups',
            enterCommand=self.makeNameString,
            textChangedCommand=self.makeNameString,
            changeCommand=self.makeNameString,
            height=height,
            font='plainLabelFont',
            editable=True,
            enableBackground=True,
            backgroundColor=backgroundColor,
            )
        cmds.textField(
            '%s_textField02' % self.windowID,
            placeholderText='Elements',
            enterCommand=self.makeNameString,
            textChangedCommand=self.makeNameString,
            changeCommand=self.makeNameString,
            height=height,
            editable=True,
            font='plainLabelFont',
            enableBackground=True,
            backgroundColor=backgroundColor,
            )
        cmds.textField(
            '%s_textField03' % self.windowID,
            placeholderText='Suffix',
            text='',
            enterCommand=self.makeNameString,
            textChangedCommand=self.makeNameString,
            changeCommand=self.makeNameString,
            height=height,
            editable=True,
            font='plainLabelFont',
            enableBackground=True,
            backgroundColor=backgroundColor,
            )

        # row1

        cmds.rowLayout(
            '%s_rowLayout02' % self.windowID,
            parent='%s_columnLayout01' % self.windowID,
            numberOfColumns=3,
            columnAlign3=('left', 'left', 'right'),
            columnAttach3=('both', 'both', 'both'),
            columnWidth3=(WIDTH / 3, WIDTH / 3, WIDTH / 3),
            height=height,
            enableBackground=True,
            backgroundColor=backgroundColor,
            )
        cmds.optionMenu(
            '%s_optionMenu01' % self.windowID,
            label='Group:',
            changeCommand=self.optionMenu01_changeCommand,
            alwaysCallChangeCommand=True,
            height=height,
            enableBackground=True,
            backgroundColor=backgroundColor,
            )
        cmds.optionMenu('%s_optionMenu02' % self.windowID, label='',
                        changeCommand=self.optionMenu02_changeCommand,
                        height=height, alwaysCallChangeCommand=True)
        cmds.optionMenu('%s_optionMenu03' % self.windowID, label='Type:'
                        ,
                        changeCommand=self.optionMenu03_changeCommand,
                        height=height, alwaysCallChangeCommand=True)

        # height=24

        cmds.separator(parent='%s_columnLayout01' % self.windowID,
                       style='none', height=6)

        cmds.rowLayout(
            '%s_rowLayout03' % self.windowID,
            parent='%s_columnLayout01' % self.windowID,
            numberOfColumns=4,
            columnAlign4=('left', 'left', 'left', 'left'),
            columnAttach4=('both', 'both', 'both', 'right'),
            columnWidth4=(WIDTH / 3, WIDTH / 6, WIDTH / 6, WIDTH
                          * 0.20),
            width=WIDTH,
            )

        # height=24

        cmds.separator(parent='%s_columnLayout01' % self.windowID,
                       style='none', height=6)

        cmds.button(
            '%s_button02' % self.windowID,
            parent='%s_rowLayout03' % self.windowID,
            label='Create Shader Group',
            command=self.createShader,
            height=height,
            enable=True,
            )
        cmds.button(
            '%s_button01' % self.windowID,
            parent='%s_rowLayout03' % self.windowID,
            label='Rename',
            command=self.rename,
            height=height,
            enable=True,
            )
        cmds.button(
            '%s_button03' % self.windowID,
            parent='%s_rowLayout03' % self.windowID,
            label='Assign',
            command=self.assignShader,
            height=height,
            enable=True,
            )
        cmds.checkBox('%s_checkBox01' % self.windowID, label='Make PSD')

    def rename(self, *args):
        dagSel = cmds.ls(selection=True)

        self.makeNameString()

        if dagSel != []:
            self.doIt()
            self.updateUI(updateWindow=True)

    def assignShader(self):
        self.makeNameString()

        sel = cmds.ls(selection=True)
        rel = cmds.listRelatives(sel, allDescendents=True, type='mesh',
                                 path=True)

        if cmds.objExists(self.newName) is True:
            pass
        else:
            print '# Shader \'%s\' doesn\'t exist. Skipping.' \
                % self.newName
            return

        try:
            cmds.select(rel)
            cmds.hyperShade(assign=self.newName)
        except:
            pass
        cmds.select(sel)

        self.updateUI(updateWindow=True)

    def createShader(self, *args):
        self.makeNameString()

        sel = cmds.ls(selection=True)
        rel = cmds.listRelatives(sel, allDescendents=True, type='mesh',
                                 path=True)

        if cmds.objExists(self.newName) is True:
            print '# Shader \'%s\' already exists. Skipping.' \
                % self.newName
            newShader = self.newName
            return None
        else:
            newShader = cmds.shadingNode(self.shaderType,
                    asShader=True, name=self.newName)

            if cmds.objExists(str(newShader) + 'SG'):
                shading_group = str(newShader) + 'SG'
            else:
                shading_group = cmds.sets(name=str(newShader) + 'SG',
                        renderable=True, noSurfaceShader=True,
                        empty=True)
        try:

            # Assign Shader

            cmds.select(rel)
            cmds.hyperShade(assign=newShader)
            self.rename()
            cmds.select(sel)
        except:
            cmds.select(newShader)

        # Add PSD file

        addPSD = cmds.checkBox('%s_checkBox01' % self.windowID,
                               query=True, value=True)
        if addPSD:
            ac = autoConnect.AutoConnect()
            ac.createPSDFile(newShader, apply=True)

        self.updateUI(updateWindow=True)

    def updateUI(self, updateWindow=False):
        """
        Update the Custom Renamer module values
        """

        global window
        global rsUtility

        shaderUtility.update()

        grps = shaderUtility.getShaderGroups()

        def _selectOptionMenuItem(optionMenu, value):
            items = cmds.optionMenu(optionMenu, query=True,
                                    itemListShort=True)
            if not items:
                return
            for (index, item) in enumerate(cmds.optionMenu(optionMenu,
                    query=True, itemListShort=True)):
                label = cmds.menuItem(item, query=True, label=True)
                if label != value:
                    continue
                cmds.optionMenu(optionMenu, edit=True, select=index + 1)

        # Menu1

        if cmds.optionMenu('%s_optionMenu01' % self.windowID,
                           query=True, numberOfItems=True) > 0:
            value = cmds.optionMenu('%s_optionMenu01' % self.windowID,
                                    query=True, value=True)
            for item in cmds.optionMenu('%s_optionMenu01'
                    % self.windowID, query=True, itemListLong=True):
                cmds.deleteUI(item)
        else:
            value = None

        if grps.keys() == []:
            return False
        if grps.keys() is None:
            return False

        if grps.keys() != []:
            for item in util.natsort(grps.keys()):
                cmds.menuItem(label=item, parent='%s_optionMenu01'
                              % self.windowID)
                if value is not None:
                    _selectOptionMenuItem('%s_optionMenu01'
                            % self.windowID, value)

        # Menu2

        key = value
        if key is None:
            return False

        if cmds.optionMenu('%s_optionMenu02' % self.windowID,
                           query=True, numberOfItems=True) > 0:
            value = cmds.optionMenu('%s_optionMenu02' % self.windowID,
                                    query=True, value=True)
            for item in cmds.optionMenu('%s_optionMenu02'
                    % self.windowID, query=True, itemListLong=True):
                cmds.deleteUI(item)
        else:
            value = None

        if key in grps.keys():
            for item in util.natsort(grps[key]):
                cmds.menuItem(label=item, parent='%s_optionMenu02'
                              % self.windowID)
                if value is not None:
                    _selectOptionMenuItem('%s_optionMenu02'
                            % self.windowID,
                            cmds.textField('%s_textField02'
                            % self.windowID, query=True, text=True))

        value = cmds.optionMenu('%s_optionMenu03' % self.windowID,
                                query=True, value=True)
        if value is None:
            for item in SHADER_TYPES:
                cmds.menuItem(item, label=item, parent='%s_optionMenu03'
                               % self.windowID)

        # Update the main Render Setup Window to reflect new group assignments

        if updateWindow:
            cmds.evalDeferred(window.updateUI)


class RenderSetupUtilityWindow(MayaQWidgetDockableMixin,
    QtWidgets.QWidget):

    """
    Main class to create the Render Setup Utility window
    """

    toolName = windowID

    def __init__(self, parent=None):
        self.deleteInstances()

        super(RenderSetupUtilityWindow, self).__init__(parent=parent)
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        self.setObjectName(windowID)

        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(windowTitle)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)

        # Set window Layout

        QVBoxLayout = QtWidgets.QVBoxLayout(self)
        QVBoxLayout.setObjectName('%s%s' % (windowID, 'QVBoxLayout'))
        QVBoxLayout.setContentsMargins(0, 0, 0, 0)
        QVBoxLayout.setSpacing(0)
        self.setLayout(QVBoxLayout)

        self.gwCustomRenamer = None

    def deleteInstances(self):

        # Delete child windows

        if cmds.window(windowNewLayerID, exists=True):
            cmds.deleteUI(windowNewLayerID)
        if cmds.window(windowNewShaderID, exists=True):
            cmds.deleteUI(windowNewShaderID)

        # Delete the workspaceControl

        control = windowID + windowWorkspaceControl
        if cmds.workspaceControl(control, q=True, exists=True):
            cmds.workspaceControl(control, e=True, close=True)
            print '# Deleting control {0}'.format(control)
            cmds.deleteUI(control, control=True)

        # Delete the instance

        for obj in QtWidgets.QApplication.allWidgets():

            if type(obj) is QtWidgets.QWidget:
                if obj.objectName() == windowID:
                    cmds.workspaceControl(windowID
                            + windowWorkspaceControl, query=True,
                            exists=True)
                    print '# Deleting instance {0}'.format(obj)

                    # Delete it for good

                    obj.setParent(None)
                    obj.deleteLater()

    def createUI(self):
        """
        Create the Render Setup Utility window
        """

        q.getQItem(windowID, QtWidgets.QWidget)
        cmds.setParent(q.fullPath)

        # ################################################
        # Active Render Layer

        cmds.separator(height=12, style='none')
        addFrameLayout('%s_frameLayoutLayers' % windowID,
                       'Visible Render Layer', collapsable=False,
                       labelVisible=False, marginHeight=0)
        addRowLayout('%s_rowLayoutActiveRenderLayer' % windowID, 3,
                     columnAlign3=('left', 'left', 'right'),
                     columnAttach3=('left', 'both', 'right'),
                     columnWidth3=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.075, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.85,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.075))
        addButton('%s_addNewLayer' % windowID, 'New', rsAddNewLayer,
                  image='RS_create_layer', size=(21, 21))
        addOptionMenu('%s_selectActiveLayer' % windowID,
                      'Active Layer    ', (), rsSelectActiveLayer)
        addButton('rsOpenRenderSetupWindow', 'Edit',
                  rsOpenRenderSetupWindow, image='render_setup.png',
                  size=(21, 21))

        # ################################################
        # Work Render Layers

        cmds.setParent(q.fullPath)
        addFrameLayout('%s_frameLayoutLayersB' % windowID,
                       'Work Render Layer', collapsable=False,
                       labelVisible=False, marginHeight=0)
        addRowLayout('%s_rowLayoutVisibleRenderLayer' % windowID, 3,
                     columnAlign3=('left', 'left', 'right'),
                     columnAttach3=('left', 'both', 'right'),
                     columnWidth3=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.075, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.85,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.075))

        cmds.separator()
        addOptionMenu('%s_selectVisibleLayer' % windowID,
                      'Visible Layer   ', (), rsSelectVisibleLayer)
        cmds.separator()

        cmds.setParent(q.fullPath)
        cmds.separator(height=12, style='none')

        # ################################################
        # Collections

        addFrameLayout('%s_frameLayout02' % windowID, 'Collections',
                       labelVisible=False, marginHeight=0)

        addRowLayout('%s_rowLayout02' % windowID, 6, columnAlign6=(
            'left',
            'left',
            'left',
            'left',
            'left',
            'left',
            ), columnAttach6=(
            'both',
            'both',
            'right',
            'right',
            'right',
            'right',
            ), columnWidth6=(
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.18,
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.18,
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.415,
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.075,
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.075,
            (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.075,
            ))

        addButton('rsAddCollection', 'Add', rsAddCollection)
        addButton('rsRemoveCollection', 'Remove', rsRemoveCollection)
        addButton('rsSelectShapes', 'Select Shapes', rsSelectShapes,
                  image='selectObject.png', size=(21, 21))
        addButton('rsRenameShader', 'Rename Shader', rsRenameShader,
                  size=(21, 21), image='QR_rename.png')
        addButton('rsDuplicateShader', 'Duplicate Shader',
                  duplicateShader, size=(21, 21), image='newPreset.png')
        addButton('rsRefreshUI', 'Refresh', rsRefreshUI, size=(21, 21),
                  image='QR_refresh.png')

        # ###########################
        # Filter List

        cmds.setParent('%s_frameLayout02' % windowID)
        addRowLayout('%s_rowLayout03' % windowID, 2,
                     columnAlign2=('left', 'left'),
                     columnAttach2=('both', 'both'),
                     columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.6, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.42))

        addTextField('%s_filterShaderList' % windowID, 'Search',
                     rsFilterShaderList_off, rsFilterShaderList_off,
                     window.updateUI)
        addOptionMenu('rsShaderGroups', '|', (), rsShaderGroups)

        # ###########################
        # The shaders scroll list

        cmds.setParent('%s_frameLayout02' % windowID)
        addRowLayout('%s_rowLayout04' % windowID, 1, columnAlign1='both'
                     , columnAttach1='both', columnWidth1=WINDOW_WIDTH
                     + 12)
        addTextScrollList('%s_ShaderScrollList' % windowID, (),
                          rsShaderScrollList_doubleClick,
                          rsShaderScrollList_onSelect,
                          rsShaderScrollList_deleteKey)

        # Add popup menu:

        cmds.popupMenu('rsShaderScrollListPopupMenu',
                       parent='%s_ShaderScrollList' % windowID,
                       allowOptionBoxes=False, markingMenu=True,
                       postMenuCommand=postMenuCommand)
        cmds.menuItem('%s_popupMenuItem02' % windowID,
                      label='Duplicate Shader', command=duplicateShader)
        cmds.menuItem(divider=True)
        cmds.menuItem('%s_popupMenuItem04' % windowID,
                      label='Graph Shader')
        cmds.menuItem(divider=True)
        cmds.menuItem('%s_popupMenuItem03' % windowID,
                      label='Select Shader')
        cmds.menuItem(divider=True)
        cmds.menuItem('%s_popupMenuItem05' % windowID,
                      label='Select Assigned Shapes')
        cmds.menuItem('%s_popupMenuItem06' % windowID,
                      label='Select Assigned Transforms')

        # ##################################################
        # Arnold Property Overrides

        cmds.setParent('%s_frameLayout02' % windowID)
        cmds.columnLayout(
            '%s_columnLayout20' % windowID,
            width=WINDOW_WIDTH - FRAME_MARGIN * 2,
            columnAlign='left',
            columnAttach=('left', 0),
            adjustableColumn=False,
            rowSpacing=0,
            )

        cmds.separator(parent='%s_columnLayout20' % windowID, height=4,
                       style='none')

        addRowLayout('%s_rowLayout05' % windowID, 2,
                     columnAlign2=('left', 'both'),
                     columnAttach2=('left', 'right'),
                     columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.75, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.25))
        addText('%s_textArnoldPropertyOverridesLabel' % windowID,
                'Apply Arnold Property Overrides', 'plainLabelFont')
        addCheckBox('rsArnoldPropertyOverridesCheckBox', '',
                    rsArnoldPropertyOverridesCheckBox,
                    rsArnoldPropertyOverridesCheckBox)
        cmds.separator(parent='%s_columnLayout20' % windowID, height=4,
                       style='none')

        # Column Layout to toggle

        cmds.setParent('%s_columnLayout20' % windowID)
        cmds.columnLayout(
            '%s_columnLayout02' % windowID,
            width=WINDOW_WIDTH - FRAME_MARGIN * 2,
            columnAlign='left',
            columnAttach=('left', 0),
            adjustableColumn=False,
            rowSpacing=0,
            )

        addCheckboxes('%s_columnLayout02' % windowID)
        cmds.columnLayout('%s_columnLayout02' % windowID, edit=True,
                          visible=False)

        # #################################################
        # Shader Override

        cmds.setParent('%s_frameLayout02' % windowID)
        cmds.columnLayout(
            '%s_columnLayout21' % windowID,
            width=WINDOW_WIDTH - FRAME_MARGIN * 2,
            columnAlign='left',
            columnAttach=('left', 0),
            adjustableColumn=False,
            rowSpacing=0,
            )
        cmds.separator(parent='%s_columnLayout21' % windowID, height=4,
                       style='none')
        addRowLayout('%s_rowLayout06' % windowID, 2,
                     columnAlign2=('left', 'right'),
                     columnAttach2=('left', 'right'),
                     columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.75, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.25))
        addText('%s_shaderOverrideLabel' % windowID, 'Shader Override',
                'plainLabelFont')
        addCheckBox('%s_shaderOverrideCheckbox' % windowID, '',
                    rsShaderOverrideCheckbox, rsShaderOverrideCheckbox)
        cmds.separator(parent='%s_columnLayout21' % windowID, height=4,
                       style='none')

        cmds.setParent('%s_columnLayout21' % windowID)
        cmds.columnLayout(
            '%s_columnLayout03' % windowID,
            width=WINDOW_WIDTH - FRAME_MARGIN * 2,
            columnAlign='left',
            columnAttach=('both', 4),
            adjustableColumn=True,
            rowSpacing=0,
            )
        cmds.setParent('%s_columnLayout03' % windowID)
        addOptionMenu('%s_optionMenu02' % windowID, 'Select: ', (),
                      rsShaderOverridesMenu)

        global selectedShaderOverride

        # default selection

        selectedShaderOverride = SHADER_OVERRIDE_OPTIONS[0]['ui']
        cmds.columnLayout('%s_columnLayout03' % windowID, edit=True,
                          visible=False)

        # #################################################

        cmds.setParent(q.fullPath)
        cmds.separator(height=10, style='none')

        # #################################################
        # Extras

        addFrameLayout('%s_frameLayout50' % windowID, 'Extras',
                       collapsable=True, marginHeight=0,
                       labelVisible=False)

        # #################################################
        # Add & Assign Shader Groups

        addFrameLayout(
            '%s_frameLayout05' % windowID,
            'Add & Assign Shader Groups',
            collapsable=True,
            marginWidth=0,
            marginHeight=0,
            collapse=False,
            labelVisible=False,
            )

        # Add the renamer window

        self.gwCustomRenamer = CustomRenamer()
        self.gwCustomRenamer.createUI()

        # #################################################
        # AutoConnect

        cmds.setParent('%s_frameLayout50' % windowID)

        addFrameLayout(
            '%s_frameLayout03' % windowID,
            'Adobe Connector',
            collapsable=True,
            marginWidth=0,
            marginHeight=0,
            collapse=True,
            labelVisible=True,
            )
        addRowLayout('%s_rowLayout07', 3, columnAlign3=('left', 'left',
                     'left'), columnAttach3=('both', 'both', 'both'),
                     columnWidth3=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.4, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.3,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.3))
        addButton('updateConnections', '> Update Connections <',
                  updateConnections)
        addButton('uvSnapshot', 'UV Snapshot', uvSnapshot)
        addButton('editTexture', 'Edit Texture', editTexture)

        # After Effects

        cmds.setParent('%s_frameLayout03' % windowID)
        addRowLayout('%s_rowLayout11' % windowID, 2,
                     columnAlign2=('left', 'left'),
                     columnAttach2=('both', 'both'),
                     columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.4, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.6))
        addText('%s_text90' % windowID, 'Send to After Effects:')
        addButton('makeCompButton', 'Send to After Effects', rsMakeComp)

        # #################################################
        # Render Setup /
        # Output settings

        cmds.setParent('%s_frameLayout50' % windowID)
        addFrameLayout(
            '%s_frameLayout04' % windowID,
            'Output Settings',
            collapsable=True,
            marginWidth=0,
            marginHeight=0,
            collapse=True,
            labelVisible=True,
            )
        addRowLayout('%s_rowLayout08' % windowID, 1,
                     columnAlign1='center', columnAttach1='both',
                     columnWidth1=WINDOW_WIDTH - FRAME_MARGIN * 2)
        addButton('%s_revealOutputDirectory' % windowID,
                  'Output path not set yet', rsRevealOutputDirectory)

        cmds.setParent('%s_frameLayout04' % windowID)
        addRowLayout('%s_rowLayout09' % windowID, 3,
                     columnAlign3=('left', 'right', 'right'),
                     columnAttach3=('left', 'right', 'right'),
                     columnWidth3=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.8, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.14,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.06))

        addOptionMenu('%s_optionMenu05' % windowID, '', (),
                      rsSelectOutputTemplate)
        addOptionMenu('%s_outputVersionMenu' % windowID, '', (),
                      rsSelectOutputVersion)
        cmds.menuItem(label='v001')

        cmds.setParent('%s_rowLayout09' % windowID)
        addButton('%s_incrementOutputVersionButton' % windowID, '+1',
                  rsIncrementOutputVersion, size=(21, 21))

        cmds.setParent('%s_frameLayout04' % windowID)
        addRowLayout('%s_rowLayout10' % windowID, 2,
                     columnAlign2=('left', 'left'),
                     columnAttach2=('both', 'right'),
                     columnWidth2=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.7, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.3))
        addOptionMenu('%s_optionMenu03' % windowID, 'Format:', (),
                      rsOutputTemplatesMenu)
        addOptionMenu('%s_optionMenu06' % windowID, '', (),
                      rsSetFPSMenu)

        cmds.setParent('%s_frameLayout04' % windowID)
        addRowLayout('%s_rowLayout12' % windowID, 4,
                     columnAlign4=('right', 'left', 'right', 'left'),
                     columnAttach4=('both', 'both', 'both', 'both'),
                     columnWidth4=((WINDOW_WIDTH - FRAME_MARGIN * 2)
                     * 0.50, (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.15,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.20,
                     (WINDOW_WIDTH - FRAME_MARGIN * 2) * 0.15))

        addText('%s_setInFrameLabel' % windowID, 'In Frame ')
        addTextField('%s_setInFrame' % windowID, '', setInFrame,
                     setInFrame, setInFrame)

        addText('%s_setOutFrameLabel' % windowID, 'Out Frame ')
        addTextField('%s_setOutFrame' % windowID, '', setOutFrame,
                     setOutFrame, setOutFrame)

    def updateUI(self, updateRenderSetup=False):
        """
        Update Render Setup Window and values
        """

        global rsUtility
        global currentSelection
        global propertyOverridesMode

        shaderUtility.update()

        q.getQItem(windowID, QtWidgets.QWidget)
        q.widget.setUpdatesEnabled(False)  # Pause qt draw temporarily

        self.gwCustomRenamer.updateUI(updateWindow=False)

        # Update Render layer Setup

        if updateRenderSetup is True:
            if rsUtility.activeLayer.needsRefresh():
                rsUtility.activeLayer.apply()

        # Housekeeping:

        rsUtility.removeMissingSelections()

        # Reapply custom QT style:

        windowStyle.apply(windowStyle)

        # #############################################
        # Active/Visible Render Layer

        listItem = []
        currentName = \
            renderSetup.instance().getVisibleRenderLayer().name()
        for l in renderSetup.instance().getRenderLayers():
            listItem.append(l.name())

            q.getQItem('%s_selectVisibleLayer' % windowID,
                       QtWidgets.QWidget)

            resetOptionMenu(q.fullPath, util.natsort(listItem), rl=True)
            selectOptionMenuItem(q.fullPath, currentName)

        # #############################################
        # Active/Visible Render Layer

        listItem = []
        currentName = rsUtility.activeLayer.name()
        for l in renderSetup.instance().getRenderLayers():
            listItem.append(l.name())

        q.getQItem('%s_selectActiveLayer' % windowID, QtWidgets.QWidget)

        resetOptionMenu(q.fullPath, util.natsort(listItem), rl=True)
        selectOptionMenuItem(q.fullPath, currentName)

        # #################
        # Button

        if cmds.optionMenu(q.fullPath, q=True, value=True) \
            == rsUtility.defaultName:
            q.getQItem('rsAddCollection', QtWidgets.QWidget)
            cmds.button(q.fullPath, edit=True, enable=False)
            q.getQItem('rsRemoveCollection', QtWidgets.QWidget)
            cmds.button(q.fullPath, edit=True, enable=False)
        else:
            q.getQItem('rsAddCollection', QtWidgets.QWidget)
            cmds.button(q.fullPath, edit=True, enable=True)
            q.getQItem('rsRemoveCollection', QtWidgets.QWidget)
            cmds.button(q.fullPath, edit=True, enable=True)

        # #############################################
        # Collections

        customStrings = []
        cleanList = []
        q.getQItem('%s_ShaderScrollList' % windowID, QtWidgets.QWidget)
        cmds.textScrollList(q.fullPath, edit=True, removeAll=True)

        def _spacer(inString):
            num = int(30 - len(inString))
            if num > 0:

                # return util.addChars(' ', num)

                return '   '
            else:
                return ' '

        # Loop through shader list

        for shaderName in shaderUtility.data.keys():
            c = rsUtility.activeLayer.collection(shaderName.replace(':'
                    , '_'), isQuery=True)

            # Mark item as inactive if not in the collections list

            if c is None:

                # Set the custom string of the shader.
                # The custom string used by the Qt delegate for custom display and to indicate if the item is active or inactive.

                shaderUtility.data[shaderName]['customString'] = \
                    '%s%s%s)' % (shaderName, ' ', '('
                                 + str(len(shaderUtility.data[shaderName]['usedBy'
                                 ])))
            else:

            # Mark item as active if in the collections list

                # Get current override values

                for (index, item) in \
                    enumerate(rsUtility.overrideAttributes):
                    try:

                        rsUtility.overrideAttributes[index][item['default'
                                ]] = c.getOverrideValue(item['long'])
                    except:
                        print '# Couldn\'t get attribute value for ' \
                            + item['long'] + '.'

                def _get(item):
                    val = c.getOverrideValue(item['long'])
                    if val is None:
                        return ''
                    else:
                        return item['custom'][1 - val]

                # Add warning if usedBy doesn't match collection selection

                WARNING = ''
                if c.selection.asList() \
                    != list(shaderUtility.data[shaderName]['usedBy']):
                    WARNING = '!!'
                SHADER_OVERRIDE = ''
                if _hasOverride(shaderName):
                    SHADER_OVERRIDE = '#'
                shaderUtility.data[shaderName]['customString'] = \
                    '%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % (
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
                    _get(rsUtility.overrideAttributes[9]),
                    _get(rsUtility.overrideAttributes[10]),
                    str(len(shaderUtility.data[shaderName]['usedBy'])),
                    WARNING,
                    SHADER_OVERRIDE,
                    )
            customStrings.append(shaderUtility.data[shaderName]['customString'
                                 ])
            cleanList.append(shaderName)

        q.getQItem('%s_filterShaderList' % windowID, QtWidgets.QWidget)
        filter = cmds.textField(q.fullPath, query=True, text=True)
        filteredList = []
        if filter != '<Lights>' and filter != '<Environment>' \
            and filter != '<Shaders>' and filter != '<StandIns>':
            filteredList = [s for s in customStrings if filter.lower()
                            in s.lower()]
        else:
            if filter == '<Lights>':
                filteredList = [s for s in customStrings
                                if shaderUtility.data[shaderUtility.customStringToShaderName(s)]['light'
                                ]]
            if filter == '<Environment>':
                filteredList = [s for s in customStrings
                                if shaderUtility.data[shaderUtility.customStringToShaderName(s)]['environment'
                                ]]
            if filter == '<Shaders>':
                filteredList = [s for s in customStrings
                                if shaderUtility.data[shaderUtility.customStringToShaderName(s)]['shader'
                                ]]
            if filter == '<StandIns>':
                filteredList = [s for s in customStrings
                                if shaderUtility.data[shaderUtility.customStringToShaderName(s)]['standIn'
                                ]]

        q.getQItem('%s_ShaderScrollList' % windowID, QtWidgets.QWidget)

        for item in util.natsort(filteredList, filterOn=True):
            cmds.textScrollList(q.fullPath, edit=True, append=item)

        # Re-Set selected items from saved selection.

        matches = set([])

        if currentSelection is not None:
            matches = set(currentSelection).intersection(set(cleanList))
        for match in matches:
            cmds.textScrollList(q.fullPath, edit=True,
                                selectItem=shaderUtility.data[match]['customString'
                                ])

        # Set height

        _setTextScrollListVisibleItemNumber()

        # Style scrollist

        numItems = len(filteredList)
        windowStyle.apply(windowStyle)

        # Checkboxes

        propertyOverridesMode = setPropertyOverridesMode()

        # Shader Overrides

        listItem = []
        menuName = '%s_optionMenu02' % windowID
        for item in SHADER_OVERRIDE_OPTIONS:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)
        setShaderOverrideMode()

        # #############################################
        # Filter list

        resetOptionMenu('rsShaderGroups',
                        util.natsort(shaderUtility.getShaderGroups().keys()),
                        rl=False)
        filterListText = cmds.textField('%s_filterShaderList'
                % windowID, query=True, text=True)
        selectOptionMenuItem('rsShaderGroups', filterListText, rl=False)

        # ############################################
        # Render output templates
        # Output format

        listItem = []
        menuName = '%s_optionMenu03' % windowID
        for item in renderOutput.SIZE_TEMPLATE:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)

        # Check current resolution

        currentWidth = cmds.getAttr('%s.width'
                                    % renderOutput.RESOLUTION_NODE)
        currentHeight = cmds.getAttr('%s.height'
                % renderOutput.RESOLUTION_NODE)

        # Check if the current list corresponds to any of the predefined sizes

        current = [w for w in renderOutput.SIZE_TEMPLATE
                   if currentWidth == w['width'] and currentHeight
                   == w['height']]
        if current:
            selectOptionMenuItem(menuName, current[0]['ui'])

        _outputTemplate()

        # Playback speed
        # Populate list

        listItem = []
        menuName = '%s_optionMenu06' % windowID
        for item in renderOutput.TIME_TEMPLATE:
            listItem.append(item['ui'])
        resetOptionMenu(menuName, listItem, rl=False)

        # Get current option

        currentTime = cmds.currentUnit(query=True, time=True)
        current = [t for t in renderOutput.TIME_TEMPLATE if currentTime
                   == t['name']]
        if current:
            selectOptionMenuItem('%s_optionMenu06' % windowID,
                                 current[0]['ui'])

        # In and out frames:

        cmds.textField('%s_setInFrame' % windowID, edit=True,
                       text=int(cmds.getAttr('defaultRenderGlobals.startFrame'
                       )))
        cmds.textField('%s_setOutFrame' % windowID, edit=True,
                       text=int(cmds.getAttr('defaultRenderGlobals.endFrame'
                       )))

        q.getQItem(windowID, QtWidgets.QWidget)
        q.widget.setUpdatesEnabled(True)  # Pause qt draw temporarily


class WindowStyle(QtWidgets.QStyledItemDelegate):

    """
    Custom ui and delegate for model.
    """

    ROW_HEIGHT = 30
    FONT_PIXEL_SIZE = 11
    FONT_PIXEL_SIZE_OFFSET = ROW_HEIGHT / 2 / 2 + 2
    ROW_WIDTH = WINDOW_WIDTH - FRAME_MARGIN * 2 - 6

    def __init__(self, parent=None, *args):
        super(WindowStyle, self).__init__(parent=parent)

        # QtWidgets.QStyledItemDelegate.__init__(self, parent=parent, *args)

        self.warningIcon = tempfile.gettempdir() + '\RS_warning.png'
        cmds.resourceManager(saveAs=['RS_warning.png',
                             self.warningIcon])
        self.shaderOverrideIcon = tempfile.gettempdir() \
            + '\out_shadingEngine.png'
        cmds.resourceManager(saveAs=['out_shadingEngine.png',
                             self.shaderOverrideIcon])

    def sizeHint(self, option, index):
        return QtCore.QSize(self.__class__.ROW_WIDTH,
                            self.__class__.ROW_HEIGHT)

    def paint(
        self,
        painter,
        option,
        index,
        ):
        """
        Main paint function for the Render Setup Utility
        """

        q.getQItem('%s_ShaderScrollList' % windowID,
                   QtWidgets.QListWidget)

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

        leadRectangleWidth = 4
        textSpacer = 4
        leadTextMargin = leadRectangleWidth * 2 + textSpacer

        # Items

        allItems = cmds.textScrollList('%s_ShaderScrollList'
                % windowID, query=True, allItems=True)
        item = allItems[index.row()]
        value = index.data(QtCore.Qt.DisplayRole)

        # Check weather the shader is in part of the ShaderUtility.
        # I noticed sometimes with updateUI there is a latency whilst the shaderUtility updates,
        # hence I get paint errors.

        try:
            shaderUtility.data[shaderUtility.customStringToShaderName(item)]
        except:
            return False

        # Getting information about the item

        shaderName = shaderUtility.customStringToShaderName(value,
                properties=False)
        nameSpace = shaderUtility.data[shaderName]['nameSpace']
        shaderType = shaderUtility.data[shaderName]['type']
        attr = shaderUtility.customStringToShaderName(value,
                properties=True)

        # Getting visual width of the text to be drawn
        # in Maya 2017 update 4 I'm not getting the ':' anymore..

        shaderNameWidth = \
            QtGui.QFontMetrics(font).width(shaderName.split(':')[-1])

        font.setBold(False)
        font.setPixelSize(10)
        painter.setFont(font)
        nameSpaceWidth = QtGui.QFontMetrics(font).width(nameSpace)

        # Draw active items

        if shaderUtility.isActive(item):
            if 'M-' in attr:
                mOffset = leadRectangleWidth
            else:
                mOffset = 0

            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82, 133,
                                 166)))
            else:
                if shaderUtility.data[shaderName]['environment']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(70, 70,
                            90)))
                elif shaderUtility.data[shaderName]['light']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(150,
                            100, 50)))
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(90, 90,
                            90)))

            # Background rectangle

            painter.drawRect(option.rect)

            # 'Active' marker

            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 170, 100)))
            painter.drawRect(QtCore.QRect(option.rect.left(),
                             option.rect.top(), leadRectangleWidth,
                             option.rect.height()))

            # Draw namespace

            if nameSpace != ':':  # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace

                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(75, 75,
                            75)))
                    painter.drawRect(QtCore.QRect(leadRectangleWidth
                            + mOffset, option.rect.top(),
                            nameSpaceWidth + leadRectangleWidth * 2,
                            option.rect.height()))

                # Draw namespace

                painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(QtCore.QRect(leadTextMargin
                                 - leadRectangleWidth + mOffset,
                                 option.rect.top()
                                 + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                                 option.rect.width(),
                                 option.rect.height()
                                 - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                                 QtCore.Qt.AlignLeft, '%s' % nameSpace)  # vertical offset

            # Draw shader name

            painter.setPen(QtGui.QPen(QtGui.QColor(210, 210, 210)))
            font.setBold(True)
            font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
            painter.setFont(font)

            painter.drawText(QtCore.QRect(((leadRectangleWidth if nameSpace
                             != '' else 0)) + leadRectangleWidth * 3
                             + nameSpaceWidth + mOffset,
                             option.rect.top()
                             + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                             option.rect.width(), option.rect.height()
                             - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                             QtCore.Qt.AlignLeft, '%s'
                             % shaderName.split(':')[-1])  # adding text spacing then there's a name space drawn

            # Draw warning icon

            if '!!' in attr:
                QIcon = QtGui.QImage(self.warningIcon)
                if shaderUtility.data[shaderName]['environment'] \
                    is False:
                    painter.drawImage(QtCore.QPoint(((leadRectangleWidth if nameSpace
                            != '' else 0)) + leadRectangleWidth * 3
                            + nameSpaceWidth + mOffset
                            + QtGui.QFontMetrics(font).width('%s'
                            % shaderName.split(':')[-1]) + 1,
                            option.rect.top()
                            + self.__class__.ROW_HEIGHT / 2
                            - QIcon.height() / 2), QIcon)
                attr = attr.replace('!!', '')

            # If the item is a mask append a small black rectangle to mark it

            if 'M-' in attr:
                painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
                painter.drawRect(QtCore.QRect(leadRectangleWidth,
                                 option.rect.top(), leadRectangleWidth,
                                 option.rect.height()))

            # Arnold shader override and attributes

            painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
            font.setBold(False)
            font.setPixelSize(10)
            painter.setFont(font)

            if '#' in attr:  # check if the item is being overriden by a shader

                # Shader override icon

                QIcon = QtGui.QImage(self.shaderOverrideIcon)
                painter.drawImage(QtCore.QPoint(option.rect.width()
                                  - QIcon.width() - leadRectangleWidth,
                                  option.rect.top()
                                  + self.__class__.ROW_HEIGHT / 2
                                  - QIcon.height() / 2), QIcon)

                # Remove shader override character and draw arnold attributes

                attr = attr.replace('#', '')

                painter.drawText(QtCore.QRect(0, option.rect.top()
                                 + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                                 option.rect.width() - QIcon.width()
                                 - leadRectangleWidth * 2,
                                 option.rect.height()
                                 - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                                 QtCore.Qt.AlignRight,
                                 '{0}-{1}'.format(shaderType, attr))
            else:
                painter.drawText(QtCore.QRect(0, option.rect.top()
                                 + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                                 option.rect.width()
                                 - leadRectangleWidth,
                                 option.rect.height()
                                 - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                                 QtCore.Qt.AlignRight,
                                 '{0}-{1}'.format(shaderType, attr))

        # !!! Draw inactive items

        if shaderUtility.isActive(item) is False:
            if option.state & QtWidgets.QStyle.State_Selected:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(82, 133,
                                 166)))
            else:
                if shaderUtility.data[shaderName]['environment']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(40, 40,
                            70)))
                elif shaderUtility.data[shaderName]['light']:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(65, 65,
                            35)))
                else:
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(55, 55,
                            55)))

            painter.drawRect(option.rect)

            # Draw namespace

            if nameSpace != ':':  # filter when the shaderName is part of the root name space

                # Draw background rectangle for namespace

                if nameSpace != '':
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50,
                            50)))
                    painter.drawRect(QtCore.QRect(0, option.rect.top(),
                            nameSpaceWidth + leadRectangleWidth * 2,
                            option.rect.height()))

                # Draw namespace rectangle and text

                painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(QtCore.QRect(textSpacer,
                                 option.rect.top()
                                 + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                                 option.rect.width(),
                                 option.rect.height()
                                 - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                                 QtCore.Qt.AlignLeft, '%s' % nameSpace)  # vertical offset

            # Draw shader name

            painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
            font.setBold(False)
            font.setPixelSize(self.__class__.FONT_PIXEL_SIZE)
            painter.setFont(font)

            painter.drawText(QtCore.QRect(((textSpacer if nameSpace
                             != '' else 0)) + textSpacer
                             + nameSpaceWidth + leadRectangleWidth,
                             option.rect.top()
                             + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                             option.rect.width(), option.rect.height()
                             - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                             QtCore.Qt.AlignLeft, '%s'
                             % shaderName.split(':')[-1])  # adding text spacing then there's a name space drawn

            try:

                # Arnold shader override and attributes

                painter.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150)))
                font.setBold(False)
                font.setPixelSize(10)
                painter.setFont(font)

                painter.drawText(QtCore.QRect(0, option.rect.top()
                                 + self.__class__.FONT_PIXEL_SIZE_OFFSET,
                                 option.rect.width()
                                 - leadRectangleWidth,
                                 option.rect.height()
                                 - self.__class__.FONT_PIXEL_SIZE_OFFSET),
                                 QtCore.Qt.AlignRight,
                                 '{0}-{1}'.format(shaderType,
                                 attr[1:][:-1]))
            except:

                raise RuntimeError('Error drawing text.')

        # Separators

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
        painter.drawRect(QtCore.QRect(option.rect.left(),
                         option.rect.top(), option.rect.width(), 1))

        painter.restore()

    def apply(self, delegate):
        """
        Applies custom skin to the Render Setup Utility window

        """

        window.layout().setSpacing(0)
        window.layout().addStretch(1)

        for item in ['%s_frameLayoutLayers', '%s_frameLayout02',
                     '%s_rowLayout04', '%s_rowLayout03']:
            q.getQItem(item % windowID, QtWidgets.QWidget)
            q.widget.setStyleSheet('QWidget {\
                    padding:0;\
                    margin:0;\
                }'
                                   )

        q.getQItem('%s_ShaderScrollList' % windowID,
                   QtWidgets.QListWidget)

        QSize = QtCore.QSize(delegate.ROW_WIDTH, delegate.ROW_HEIGHT)

        for i in range(q.widget.count()):
            q.widget.setItemDelegateForRow(i, delegate)
            q.widget.item(i).setSizeHint(QSize)

        q.widget.setStyleSheet('QListWidget {\
                padding:0;\
                margin:0;\
                color: rgb(200,200,200);\
                background-color:rgb(60,60,60);\
                border-style:solid;\
                border-radius:2\
            }'
                               )

        # Filter list

        q.getQItem('%s_rowLayout03' % windowID, QtWidgets.QWidget)
        q.widget.setStyleSheet('QWidget {\
                background-color: rgb(60,60,60);\
                color: rgb(200,200,200);\
                padding:1 0;\
                margin:0;\
        }'
                               )

        # Arnold Propery / Shader Overrides

        for item in ['%s_columnLayout20', '%s_columnLayout21']:
            q.getQItem(item % windowID, QtWidgets.QWidget)
            q.widget.setStyleSheet('.QWidget {\
                    background-color: rgb(60,60,60);\
                    color: rgb(200,200,200);\
                    padding: 4px 0px 2px 4px;\
                    margin: 0;\
                    border-radius:2px\
                }\
                QWidget {\
                    padding: 0 4;\
                }'
                                   )

        for item in ['%s_selectActiveLayer' % windowID,
                     '%s_selectVisibleLayer' % windowID,
                     '%s_optionMenu02' % windowID, '%s_optionMenu03'
                     % windowID, '%s_outputVersionMenu' % windowID]:
            q.getQItem(item, QtWidgets.QComboBox)
            q.widget.setStyleSheet('QComboBox {\
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
        for item in ['%s_optionMenu01'
                     % window.gwCustomRenamer.windowID,
                     '%s_optionMenu02'
                     % window.gwCustomRenamer.windowID,
                     '%s_optionMenu03'
                     % window.gwCustomRenamer.windowID]:
            q.getQItem(item, QtWidgets.QComboBox)
            q.widget.setStyleSheet('QComboBox {\
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

        def setButtonStylesheet(
            inName,
            eColor,
            eBackgroundColor,
            ehColor,
            ehBackgroundColor,
            ):
            q.getQItem(inName, QtWidgets.QPushButton)
            q.widget.setStyleSheet('QPushButton {\
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
            }'
                                    % (
                eColor,
                eBackgroundColor,
                ehColor,
                ehBackgroundColor,
                dColor,
                dBackgroundColor,
                ))

        def setAdobeButtonStylesheet(
            inName,
            eColor,
            eBackgroundColor,
            ehBackgroundColor,
            ):
            q.getQItem(inName, QtWidgets.QPushButton)
            q.widget.setStyleSheet('QPushButton {\
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
            }'
                                    % (
                eColor,
                eBackgroundColor,
                eColor,
                eColor,
                ehBackgroundColor,
                eColor,
                eBackgroundColor,
                ))

        eColor = '200,200,200'
        eBackgroundColor = '95,95,95'
        ehColor = '230,230,230'
        ehBackgroundColor = '100,100,100'
        dColor = '95,95,95'
        dBackgroundColor = '68,68,68'

        for item in [
            'rsAddCollection',
            'rsRemoveCollection',
            'updateConnections',
            '%s_incrementOutputVersionButton' % windowID,
            '%s_button01' % window.gwCustomRenamer.windowID,
            '%s_button02' % window.gwCustomRenamer.windowID,
            '%s_button03' % window.gwCustomRenamer.windowID,
            ]:
            setButtonStylesheet(item, eColor, eBackgroundColor,
                                ehColor, ehBackgroundColor)
        for item in ['editTexture', 'uvSnapshot']:
            setAdobeButtonStylesheet(item, '27, 198, 251', '0,29,38',
                    '0,39,48')
        setAdobeButtonStylesheet('makeCompButton', '198,140,248',
                                 '31,0,63', '41,0,73')

        for item in ['%s_filterShaderList' % windowID, '%s_textField01'
                     % window.gwCustomRenamer.windowID, '%s_textField02'
                      % window.gwCustomRenamer.windowID,
                     '%s_textField03'
                     % window.gwCustomRenamer.windowID]:
            q.getQItem(item, QtWidgets.QLineEdit)
            q.widget.setStyleSheet('QLineEdit {\
                background-color: rgb(60,60,60);\
                padding:2 2;\
                margin:0;\
            }'
                                   )

        # Arnold Property override checkbox labels

        for (index, item) in enumerate(rsUtility.overrideAttributes):
            q.getQItem('%s_text%s' % (windowID, str(index).zfill(2)),
                       QtWidgets.QLabel)
            q.widget.setStyleSheet('QLabel {\
                border-style: dashed;\
                border-width: 0 0 1px 0;\
                border-color: rgb(50,50,50);\
                color: rgb(175,175,175);\
                font-size: 10px;\
                margin-left: 0;\
                margin-bottom: 2\
            }'
                                   )

        q.getQItem('%s_revealOutputDirectory' % windowID,
                   QtWidgets.QPushButton)
        q.widget.setStyleSheet('QPushButton {\
            color: rgb(150,150,150);\
            background-color: rgb(50,50,50);\
            border: none;\
            border-radius: 2px;\
            font-size:12px\
        }'
                               )

        q.getQItem('rsShaderGroups', QtWidgets.QComboBox)
        q.widget.setStyleSheet('QComboBox {\
                color: rgb(150,150,150);\
                background-color: rgb(60,60,60);\
                font-size:11px\
                }\
            }'
                               )


global _cbs
_cbs = []
global isWindowVisible
isWindowVisible = False


def _cb_kAfterNew(clientData):
    import maya.utils as mUtils
    try:
        if isWindowVisible:
            createUI()
    except Exception, e:
        print 'Callback error({0}): {1}'.format(e.errno, e.strerror)


def _cb_kAfterOpen(clientData):
    import maya.utils as mUtils
    try:
        if isWindowVisible:
            createUI()
    except Exception, e:
        print 'Callback error({0}): {1}'.format(e.errno, e.strerror)


def _cb_kBeforeNew(clientData):
    import maya.utils as mUtils

    global _cbs
    global isWindowVisible
    isWindowVisible = \
        cmds.workspaceControl(RenderSetupUtilityWindow.toolName
                              + windowWorkspaceControl, query=True,
                              visible=True)

    global currentSelection
    currentSelection = None
    global selectedShaderOverride
    selectedShaderOverride = None
    global overrideShader
    overrideShader = None

    global rsUtility
    rsUtility = None

    global rsRenderOutput
    rsRenderOutput = None
    shaderUtility = None
    global window
    window = None
    global windowStyle
    windowStyle = None

    for cb in _cbs:
        OpenMaya.MSceneMessage.removeCallback(cb)
    _cbs = []

    def _del():
        clientData.deleteInstances()

    _del()


def _cb_kBeforeOpen(clientData):
    import maya.utils as mUtils
    global _cbs

    global isWindowVisible
    isWindowVisible = \
        cmds.workspaceControl(RenderSetupUtilityWindow.toolName
                              + windowWorkspaceControl, query=True,
                              visible=True)

    global currentSelection
    currentSelection = None
    global selectedShaderOverride
    selectedShaderOverride = None
    global overrideShader
    overrideShader = None

    global rsUtility
    rsUtility = None

    global rsRenderOutput
    rsRenderOutput = None
    global window
    window = None
    global windowStyle
    windowStyle = None

    for cb in _cbs:
        OpenMaya.MSceneMessage.removeCallback(cb)
    _cbs = []

    def _del():
        clientData.deleteInstances()

    # mUtils.executeDeferred(_del)

    _del()


def createUI(eventsFilters=False):

    # Let's make sure arnold is loaded and that the arnold options are created.

    try:
        import mtoa.core as core
        core.createOptions()
    except:
        pass

    global window
    global windowStyle
    global rsUtility
    global rsRenderOutput
    global _cbs
    global isWindowVisible

    rsUtility = utility.Utility()
    rsRenderOutput = renderOutput.RenderOutput()

    window = RenderSetupUtilityWindow()
    window.show(dockable=True)  # creates the workspace control
    window.createUI()
    isWindowVisible = True

    windowStyle = WindowStyle(parent=window)

    cmds.workspaceControl(RenderSetupUtilityWindow.toolName
                          + windowWorkspaceControl, edit=True,
                          widthProperty='free')

    if len(_cbs) == 0:
        cb_kBeforeNew = \
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeNew,
                _cb_kBeforeNew, clientData=window)
        _cbs.append(cb_kBeforeNew)

        cb_kBeforeOpen = \
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeOpen,
                _cb_kBeforeOpen, clientData=window)
        _cbs.append(cb_kBeforeOpen)

        cb_kAfterNew = \
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterNew,
                _cb_kAfterNew, clientData=window)
        _cbs.append(cb_kAfterNew)

        cb_kAfterOpen = \
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterOpen,
                _cb_kAfterOpen, clientData=window)
        _cbs.append(cb_kAfterOpen)

    window.updateUI(updateRenderSetup=False)
