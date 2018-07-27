"""
Autoconnect.
"""

# pylint: disable=C0103, E0401

import base64
import os
import os.path as path
import string
from shutil import copy
import shiboken2
import _winreg
import PySide2.QtWidgets as QtWidgets
import maya.cmds as cmds
import maya.OpenMayaUI as OpenMayaUI
import RenderSetupUtility.ac.templates as templates
import RenderSetupUtility.main.renderOutput as renderOutput
from RenderSetupUtility.main.shaderUtility import ShaderUtility

SOURCE_IMAGES = 'textures'
RENDERS = 'renders'

# When parsing directories look for these extensions types.
ACCEPT_TYPES = (
    'jpg',
    'jpeg',
    'gif',
    'exr',
    'png',
    'eps',
    'pic',
    'hdr',
    'sgi',
    'tif',
    'tiff',
    'bmp',
    'xpm'
)

ATTRIBTE_TYPES = (
    {'attribute': 'color', 'type': 'float3', 'name': 'Diffuse Color'},
    {'attribute': 'Kd', 'type': 'float1', 'name': 'Diffuse Color Weight'},
    {'attribute': 'diffuseRoughness', 'type': 'float1', 'name': 'Diffuse Roughness'},
    {'attribute': 'directDiffuse', 'type': 'float1', 'name': 'Direct Diffuse Weight'},
    {'attribute': 'indirectDiffuse', 'type': 'float1', 'name': 'Indirect Diffuse Weight'},
    {'attribute': 'KsColor', 'type': 'float3', 'name': 'Specular Color'},
    {'attribute': 'Ks', 'type': 'float1', 'name': 'Specular Weight'},
    {'attribute': 'specularRoughness', 'type': 'float1', 'name': 'Specular Roughness'},
    {'attribute': 'specularAnisotropy', 'type': 'float1', 'name': 'Specular Anisotropy'},
    {'attribute': 'specularRotation', 'type': 'float1', 'name': 'Specular Rotation'},
    {'attribute': 'KrColor', 'type': 'float3', 'name': 'Reflection Color'},
    {'attribute': 'Kr', 'type': 'float1', 'name': 'Reflection Weight'},
    {'attribute': 'KtColor', 'type': 'float3', 'name': 'Refraction Color'},
    {'attribute': 'Kt', 'type': 'float1', 'name': 'Refraction Weight'},
    {'attribute': 'emissionColor', 'type': 'float3', 'name': 'Emission Color'},
    {'attribute': 'opacity', 'type': 'float3', 'name': 'Opacity'}
)



def getAdobePath(appName):
    """
    Returns the windows registry values for the latest version number found.
    """

    Registry = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
    RawKey = _winreg.OpenKey(Registry, 'SOFTWARE\Adobe\%s' % appName)

    subkeys = []
    try:
        i = 0
        while True:
            subkeys.append(_winreg.EnumKey(RawKey, i))
            i += 1
    except WindowsError:
        pass
    _winreg.CloseKey(RawKey)

    versionNumbers = sorted([float(x) for x in subkeys], reverse=True)
    for v in versionNumbers:
        try:
            RawKey = _winreg.OpenKey(
                Registry, r'SOFTWARE\Adobe\%s\%s' % (appName, str(v)))
            i = 0
            while 1:
                name, value, type = _winreg.EnumValue(RawKey, i)
                attr = {'path': value, 'version': v}
                if os.path.isdir(value):
                    _winreg.CloseKey(RawKey)
                    return attr
                i += 1
        except WindowsError:
            pass
        _winreg.CloseKey(RawKey)
        return None
        # break


def exportCamera():
    import tempfile

    AE_EXPORT_SET = 'aeExportSet'
    AE_MAIN_CAMERA = 'camera'
    AE_CAMERA = '_MayaCamera_'
    startFrame = cmds.playbackOptions(q=True, minTime=True)
    endFrame = cmds.playbackOptions(q=True, maxTime=True)

    if cmds.objExists(AE_MAIN_CAMERA) is False:
        raise RuntimeError('Make sure the main camera is called \'camera\'')

    if cmds.objExists(AE_EXPORT_SET):
        pass
    else:
        cmds.sets(name=AE_EXPORT_SET, renderable=False, empty=True)
        if cmds.objExists(AE_MAIN_CAMERA):
            cmds.sets(AE_MAIN_CAMERA, add=AE_EXPORT_SET)

    cmds.select(AE_EXPORT_SET)
    sel = cmds.ls(selection=True)
    for s in sel:
        shape = cmds.listRelatives(s, shapes=True)[0]
        if cmds.nodeType(shape) == 'camera':
            cameraShape = shape

            cmds.duplicate(AE_MAIN_CAMERA, name=AE_CAMERA, smartTransform=False,
                           upstreamNodes=False, inputConnections=False)
            cmds.parent(AE_CAMERA, world=True)

            attrs = cmds.listAttr(AE_CAMERA, locked=True)
            if attrs is not None:
                for attr in attrs:
                    cmds.setAttr('%s.%s' % (AE_CAMERA, attr), lock=False)
                try:
                    cmds.parent(AE_CAMERA, world=True)
                except:
                    pass
            parentContraint = cmds.parentConstraint(AE_MAIN_CAMERA, AE_CAMERA)

            # Bake Camera
            cmds.bakeResults(AE_CAMERA, t=(startFrame, endFrame))
            cmds.delete(parentContraint)
            break

    tempDir = tempfile.gettempdir()
    tempName = '_MayaCamera_.ma'
    path = os.path.join(tempDir, tempName)
    path = os.path.normpath(path)
    cmds.select(AE_CAMERA)
    cmds.file(path, type='mayaAscii',
              exportSelected=True, channels=True, f=True)
    cmds.delete(AE_CAMERA)

    INVALID_CHARACTERS = '{}'

    # Read the maya file
    f = open(path, 'r')
    MAYA_ASCII_DATA = f.read()
    f.close()

    lines = MAYA_ASCII_DATA.split('\n')

    idxs = []
    for invalid in INVALID_CHARACTERS:
        for index, line in enumerate(MAYA_ASCII_DATA.split('\n')):
            if invalid in line:
                idxs.append(index)

    # Sort and remove duplicates
    idxs = list(sorted(set(idxs)))

    # Let's remove the lines containing the invalid lines
    for index in idxs[::-1]:  # reverse the list
        lines.pop(index)

    # Write the maya file
    MAYA_ASCII_DATA = '\n'.join(lines)
    f = open(path, 'w')
    f.write(MAYA_ASCII_DATA)
    f.close()

    return path


class SceneInfo(object):
    """
    Utility class.

    Queries the state of the current scene and returns the appropiate paths
    if 'isSceneSaved' is true.

    """

    def __init__(self):
        self.isSceneSaved = cmds.file(query=True, exists=True)

        self.startFrame = cmds.getAttr(
            renderOutput.DEFAULTS_NODE + '.startFrame')
        self.endFrame = cmds.getAttr(renderOutput.DEFAULTS_NODE + '.endFrame')
        self.duration = int(self.endFrame - int(self.startFrame)) + 1
        self.currentTime = cmds.currentUnit(query=True, time=True)
        self.frameRate = [
            t for t in renderOutput.TIME_TEMPLATE if self.currentTime == t['name']][0]['fps']
        self.currentWidth = cmds.getAttr(
            '%s.width' % renderOutput.RESOLUTION_NODE)
        self.currentHeight = cmds.getAttr(
            '%s.height' % renderOutput.RESOLUTION_NODE)

        if self.isSceneSaved is False:
            self.sceneName = None
            self.scenePath = None
            self.workspace = None
            self.sourceImages = None
            return

        self.sceneName = cmds.file(query=True, sceneName=True, shortName=True)
        self.scenePath = os.path.normpath(cmds.file(query=True, expandName=True))
        self.workspace = os.path.normpath(cmds.workspace(query=True, rootDirectory=True))
        self.sourceImages = os.path.normpath(path.join(self.workspace, SOURCE_IMAGES))
        self.renders = os.path.normpath(path.join(self.workspace, RENDERS))


class AutoConnect(SceneInfo):
    """Querries the 'workspace/imageSource' folder and collects all folders and
    their contents corresponding to shader names in the current scene.

    doIt() - Connects the found image sources to the corresponding
    scene shader based on the name suffix assignments.
    """

    obj = getAdobePath('Photoshop')
    if obj:
        PHOTOSHOP_PATH = os.path.normpath(
            os.path.join(obj['path'], 'Photoshop.exe'))
    else:
        PHOTOSHOP_PATH = None

    AFTER_EFFECTS_PATH = None
    obj = getAdobePath('After Effects')
    if obj:
        AFTER_EFFECTS_PATH = os.path.normpath(
            os.path.join(obj['path'], 'AfterFX.exe'))

    def __init__(self):
        super(AutoConnect, self).__init__()
        self.DATA = {}

        if self.isSceneSaved is False:
            return None

        directories = [d for d in os.listdir(self.sourceImages) if os.path.isdir(
            os.path.join(self.sourceImages, d))]
        shaderList = ShaderUtility().getShaderList(
            excludeOverrides=True, excludeUnused=False)

        for directory in directories:
            if not (f for f in shaderList if f == directory):
                continue

            children = {}
            psdFile = None

            for item in os.listdir(path.join(self.sourceImages, directory)):
                if item.endswith(".psd"):
                    psdFile = item
                    continue
                if item.endswith(ACCEPT_TYPES) is False:
                    continue

                # Match name suffixes with the attributes list

                attributesFound = [f for f in ATTRIBTE_TYPES if str(
                    '_' + f['attribute'].lower()) in item.lower()]
                if attributesFound == []:
                    continue

                children[item] = {
                    'destination': directory + '.' + attributesFound[0]['attribute'],
                    'type': attributesFound[0]['type'],
                    'name': item.split('.')[0],
                    'ext': item.split('.')[1],
                    'path': path.normpath(path.join(self.sourceImages, directory, item))
                }

            if psdFile is not None:
                self.DATA[directory] = {
                    'psdPath': path.normpath(path.join(self.sourceImages, directory, psdFile)),
                    'shaderName': directory,
                    'name': directory,
                    'children': children,
                    'path': path.normpath(path.join(self.sourceImages, directory))
                }

    def update(self):
        self.__init__()

    def doIt(self, inShaders, createMissing=False):
        def _prompt():
            return cmds.confirmDialog(
                title='Shader Attribute Already Connected',
                message='%s already has a custom connection to %s.\
                \nShall I replace it with the found source?\n> %s <' % (
                    c['destination'],
                    cmds.connectionInfo(c['destination'],
                                        sourceFromDestination=True), '%s.%s' % (c['name'], c['ext'])
                ),
                button=['Overwrite', 'Cancel'],
                defaultButton='Overwrite',
                cancelButton='Cancel',
                dismissString='Cancel'
            )

        def _makeConnection(attribute):
            # No connection
            if cmds.connectionInfo(c['destination'], isDestination=True) is False:
                if cmds.isConnected('%s.%s' % (fileNode, attribute), c['destination']) is False:
                    cmds.connectAttr('%s.%s' % (
                        fileNode, attribute), c['destination'], f=True)
            if cmds.connectionInfo(c['destination'], isDestination=True) is True:
                # Custom connection
                if '%s.%s' % (fileNode, attribute) != cmds.connectionInfo(c['destination'], sourceFromDestination=True):
                    choice = _prompt()
                    if choice == 'Overwrite':
                        cmds.connectAttr('%s.%s' % (
                            fileNode, attribute), c['destination'], f=True)
                else:
                    if cmds.isConnected('%s.%s' % (fileNode, attribute), c['destination']) is True:
                        print '%s.%s already connected. Skipping.' % (
                            fileNode, attribute)

        if self.isSceneSaved is False:
            raise RuntimeError('Scene is not saved yet.')

        shaderList = ShaderUtility().getShaderList(
            excludeOverrides=True, excludeUnused=False)

        # Check if the inShader has an autoConnect setup present
        shadersWithAssociatedPSDFiles = [
            f for f in self.DATA if f in inShaders]
        if shadersWithAssociatedPSDFiles == []:
            print ('# Couldn\'t find a PSD file for the selected shader. Skipping. #')
            return

        for s in shadersWithAssociatedPSDFiles:
            if self.DATA[s]['children'].keys() == []:
                print '# PSD file is present for \'%s\' but no texture image files found. Skipping. #' % s
                continue

            for child in self.DATA[s]['children']:
                c = self.DATA[s]['children'][child]
                if cmds.objExists(c['name']) is False:
                    # Creating file and place2dTexture nodes...
                    fileNode = cmds.shadingNode(
                        "file", name=c['name'], asTexture=True)
                    place2dTexture = cmds.shadingNode(
                        "place2dTexture", name=c['name'] + '_place2dTexture', asUtility=True)
                    cmds.connectAttr("%s.outUV" % place2dTexture,
                                     "%s.uvCoord" % fileNode, f=True)
                    cmds.connectAttr(
                        "%s.outUvFilterSize" % place2dTexture, "%s.uvFilterSize" % fileNode, f=True)
                    attributes = ("coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger", "wrapU", "wrapV",
                                  "repeatUV", "vertexUvOne", "vertexUvTwo", "vertexUvThree", "vertexCameraOne", "noiseUV", "offset", "rotateUV")
                    for attribute in attributes:
                        cmds.connectAttr("%s.%s" % (place2dTexture, attribute), "%s.%s" % (
                            fileNode, attribute), f=True)
                else:
                    fileNode = c['name']
                # Set the file node path to the source image path
                cmds.setAttr('%s.fileTextureName' %
                             fileNode, c['path'], type="string")

                # Connect image file to the shader
                if c['type'] == 'float1':
                    _makeConnection('outColorR')
                if c['type'] == 'float3':
                    _makeConnection('outColor')

    def rename(self, shaderName, newShaderName='untitled'):
        """
        Renames the given AutoConnect assigned shader and the associated files
        and Maya objects.
        """

        def format_filename(s):
            valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
            filename = ''.join(c for c in s if c in valid_chars)
            # I don't like spaces in filenames.
            filename = filename.replace(' ', '')
            return filename

        newShaderName = format_filename(newShaderName)

        if [f for f in self.DATA.keys() if f == shaderName] == []:
            print('\'%s\' shader doesn\'t have an AutoConnect setup.' % shaderName)
            return False

        # Create folder with new name
        if os.path.isdir(self.DATA[shaderName]['path']):
            newFolderName = self.DATA[shaderName]['path'].replace(
                shaderName, newShaderName)
            try:
                os.makedirs(newFolderName)
            except:
                print 'Error making folder'
            print '%s -> %s' % (os.path.basename(
                self.DATA[shaderName]['path']), newFolderName)

        # Move child image files:
        for item in self.DATA[shaderName]['children']:
            obj = self.DATA[shaderName]['children'][item]
            newPath = obj['path'].replace(shaderName, newShaderName)
            if os.path.isfile(obj['path']):
                try:
                    copy(obj['path'], newPath)
                except:
                    print 'Error copying file.'
                print '%s -> %s' % (os.path.basename(
                    obj['path']), os.path.basename(newPath))

        for item in cmds.ls('%s*' % shaderName):
            newName = item.replace(shaderName, newShaderName)
            cmds.rename(item, newName)

        if os.path.isfile(self.DATA[shaderName]['psdPath']):
            newPsdPath = self.DATA[shaderName]['psdPath'].replace(
                shaderName, newShaderName)
            try:
                copy(self.DATA[shaderName]['psdPath'], newPsdPath)
            except:
                print 'Error copying file.'
            print '%s -> %s' % (os.path.basename(
                self.DATA[shaderName]['psdPath']), os.path.basename(newPsdPath))

        # Replace image path::
        for item in self.DATA[shaderName]['children']:
            obj = self.DATA[shaderName]['children'][item]

            newName = obj['name'].replace(shaderName, newShaderName)
            if cmds.objExists(newName):
                newPath = obj['path'].replace(shaderName, newShaderName)
                cmds.setAttr('%s.fileTextureName' %
                             newName, newPath, type='string')

        return True

    def createPSDFile(self, shaderName, apply=False):
        if apply is False:
            return

        dirPath = path.normpath(
            path.join(self.workspace, self.sourceImages, shaderName))
        if os.path.isdir(dirPath) is not True:
            os.mkdir(dirPath)
            print 'Folder created.'
        else:
            print 'A folder already exists at this location. No files were created.'

        if os.path.isfile('%s/%s.psd' % (dirPath, shaderName)) is not True:
            f = open('%s/%s.psd' % (dirPath, shaderName), 'w')
            PSD_TEMPLATE = base64.b64decode(templates.PSD_TEMPLATE_BASE64)
            f.write(PSD_TEMPLATE)
            f.close()
            print 'PSD file created.'
        else:
            print 'A PSD file already exists at this location. No files were created.'

        self.update()

#####################################
# Camera Export for After Effects


# Viewport Preset object
VIEWPORT_PRESET = (
    # {'displayLights':'default'},
    # {'rendererName':'vp2Renderer'},
    {'twoSidedLighting': False},
    {'displayAppearance': 'smoothShaded'},
    {'wireframeOnShaded': True},
    {'headsUpDisplay': False},
    {'selectionHiliteDisplay': False},
    {'useDefaultMaterial': False}, #
    {'imagePlane': False},
    {'useRGBImagePlane': True},
    {'backfaceCulling': False},
    {'xray': False},
    {'jointXray': False},
    {'activeComponentsXray': False},
    {'maxConstantTransparency': 1.0},
    # {'displayTextures':False},
    {'smoothWireframe': True},
    {'lineWidth': 1.0},
    {'textureAnisotropic': False},
    {'textureSampling': 2},
    {'textureDisplay': 'modulate'},
    {'textureHilight': True},
    # {'shadows':False},
    {'nurbsCurves': False},
    {'nurbsSurfaces': False},
    {'polymeshes': True},
    {'subdivSurfaces': True},
    {'planes': False},
    {'lights': False},
    {'cameras': False},
    {'controlVertices': False},
    {'grid': False},
    {'hulls': False},
    {'joints': False},
    {'ikHandles': False},
    {'deformers': False},
    {'dynamics': False},
    {'fluids': False},
    {'hairSystems': False},
    {'follicles': False},
    {'nCloths': False},
    {'nParticles': False},
    {'nRigids': False},
    {'dynamicConstraints': False},
    {'locators': False},
    {'manipulators': False},
    {'dimensions': False},
    {'handles': False},
    {'pivots': False},
    {'textures': False},
    {'strokes': False}
)


def captureWindow(width, height):
    window = QtWidgets.QWidget()
    window.resize(width, height)
    qtLayout = QtWidgets.QVBoxLayout(window)
    qtLayout.setObjectName('viewportLayout')

    cmds.setParent('viewportLayout')
    panelayoutPath = cmds.paneLayout()
    modelPanelName = cmds.modelPanel(
        "embeddedModelPanel#", cam='camera', menuBarVisible=False)

    modelEditorName = cmds.modelPanel(
        modelPanelName, query=True, modelEditor=True)

    def _get(**kwargs):
        return cmds.modelEditor(p, query=True, **kwargs)

    def _set(**kwargs):
        return cmds.modelEditor(modelEditorName, edit=True, **kwargs)
    modelPanels = cmds.getPanel(type='modelPanel')

    for p in modelPanels:
        camName = cmds.modelEditor(p, query=True, camera=True)
        if camName == 'camera':
            for item in VIEWPORT_PRESET:
                key = next(iter(item))
                if item[key] is True:
                    item[key] = _get(**item)
            break
    for item in VIEWPORT_PRESET:
        key = next(iter(item))
        _set(**item)

    cmds.setAttr("hardwareRenderingGlobals.multiSampleEnable", True)
    cmds.setAttr("hardwareRenderingGlobals.multiSampleCount", 4)
    cmds.setAttr("hardwareRenderingGlobals.ssaoEnable", True)

    ptr = OpenMayaUI.MQtUtil.findControl(panelayoutPath)
    paneLayoutQt = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
    qtLayout.addWidget(paneLayoutQt)

    window.show()
    cmds.setFocus(modelPanelName)

    return window
