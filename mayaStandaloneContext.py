# -*- coding: utf-8 -*-
# pylint: disable=E1101, I1101, C0103, C0301, R0913, E0401, C0413

"""This module initializes the Maya 2018 standalone context, loads the Maya PySide modules,
and initializes the maya.cmds and MtoA modules.

Example:
    import _initMaya
    _initMaya.initialize(**kwargs)

kwargs:
    load_plugins (bool):        Loads a set of Maya Plugins.
                                Calls the loadPlugins() function.
    load_MtoA (bool):           Loads MtoA when set to True.
                                Calls the initMtoa() function.
    populate_scene (bool):      Populates the Maya scene with the defined content.
                                To define the contents of the scene make sure to override
                                populateScene() function.

Author:
    Gergely Wootsch, 2018
    hello@gergely-wootsch.com

"""

import os
import sys

app = None # the global app variable

MAYA_LOCATION = r'C:\Program Files\Autodesk\Maya2018'
MAYA_BIN = r'C:\Program Files\Autodesk\Maya2018\bin'
MTOA_EXTENSIONS_PATH = r'C:\solidangle\mtoadeploy\2018\extensions'
QTDIR = r'C:\Python27\Lib\site-packages\PySide2'
QT_QPA_PLATFORM_PLUGIN_PATH = r'C:\Program Files\Autodesk\Maya2018\qt-plugins\platforms'
PYTHON_DLLS = r'C:\Program Files\Autodesk\Maya2018\Python\DLLs'
PYTHON_PACKAGES = r'C:\Program Files\Autodesk\Maya2018\Python\Lib\site-packages'
PYTHON_ROOT = r'C:\Program Files\Autodesk\Maya2018\Python'

MAYA_PLUGINS = (
    # 'autoLoader',
    # 'curveWarp',
    # 'GPUBuiltInDeformer',
    # 'gpuCache',
    # 'deformerEvaluator',
    # 'ik2Bsolver',
    # 'matrixNodes',
    # 'mayaCharacterization',
    # 'mayaHIK',
    # 'meshReorder',
    # 'OpenEXRLoader',
    # 'quatNodes',
    # 'retargeterNodes',
    # 'rotateHelper',
    # 'sceneAssembly',
    'mtoa',
    # 'modelingToolkit',
    # 'renderSetup',
    # 'Type',
)

MEL_SCRIPTS = (
    'defaultRunTimeCommands.res.mel',  # sourced automatically
    # 'defaultRunTimeCommands.mel',  # sourced automatically
    'createPreferencesOptVars.mel',
    'initAddAttr.mel',
    'createGlobalOptVars.mel',
    'initialStartup.mel',
    # 'initialPlugins.mel',
    'namedCommandSetup.mel',
)

os.environ["QTDIR"] = QTDIR
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = QT_QPA_PLATFORM_PLUGIN_PATH
os.environ['MAYA_LOCATION'] = MAYA_LOCATION
os.environ['PYMEL_SKIP_MEL_INIT'] = '1'
os.environ['MAYA_SKIP_USERSETUP_PY'] = '1'
os.environ['MTOA_EXTENSIONS_PATH'] = MTOA_EXTENSIONS_PATH

os.environ["PATH"] = MAYA_LOCATION + os.pathsep + os.environ['PATH']
os.environ["PATH"] = MAYA_BIN + os.pathsep + os.environ['PATH']

sys.path.insert(0, MAYA_BIN)
sys.path.insert(0, PYTHON_DLLS)
sys.path.insert(0, PYTHON_PACKAGES)
sys.path.insert(0, PYTHON_ROOT)

from PySide2 import QtWidgets
from maya import cmds, mel, standalone


def loadPlugins():
    """Loads maya plugins"""
    for script in MEL_SCRIPTS:
        mel.eval('source "{}"'.format(script))
    for plugins in MAYA_PLUGINS:
        cmds.loadPlugin(plugins)


def initMtoa():
    """Loads Arnold into the standalone context."""

    import mtoa.core as core
    core.installCallbacks()
    core.createOptions()

    from mtoa.ui.ae.shadingEngineTemplate import ShadingEngineTemplate
    import mtoa.ui.ae.templates as templates
    templates.registerAETemplate(ShadingEngineTemplate, "shadingEngine")


def populateScene():
    """Populates the Maya scene with default contents."""

    def getSG(shader):
        """Convenience function to get the ShadingGroup of a shader."""
        if not shader or not cmds.objExists(shader):
            return None
        return next((f for f in (cmds.listConnections(shader, d=True, et=True, t='shadingEngine'))), None)


    def createShader(shaderType):
        """Convenience function to create a shader."""
        shader = cmds.shadingNode(shaderType, asShader=True)
        name = '{}SG'.format(shader)
        cmds.sets(name=name, renderable=True, noSurfaceShader=True, empty=True)
        cmds.connectAttr('{}.outColor'.format(shader),
                         '{}.surfaceShader'.format(name))
        return shader

    # The Arnold5 specific shaders.
    for _ in xrange(1):
        cmds.sets(cmds.polyCube(), e=True, forceElement=getSG(
            createShader('aiStandardSurface')))
        cmds.sets(cmds.polyCube(), e=True,
                  forceElement=getSG(createShader('aiUtility')))
        cmds.sets(cmds.polyCube(), e=True,
                  forceElement=getSG(createShader('aiToon')))
        cmds.sets(cmds.polyCube(), e=True, forceElement=getSG(
            createShader('aiAmbientOcclusion')))
        cmds.sets(cmds.polyCube(), e=True, forceElement=getSG(
            createShader('aiMotionVector')))
        cmds.sets(cmds.polyCube(), e=True, forceElement=getSG(
            createShader('aiShadowMatte')))
        cmds.sets(cmds.polyCube(), e=True, forceElement=getSG(
            createShader('aiRaySwitch')))
        cmds.sets(cmds.polyCube(), e=True,
                  forceElement=getSG(createShader('aiSkin')))
        cmds.sets(cmds.polyCube(), e=True,
                  forceElement=getSG(createShader('aiHair')))
        cmds.sets(cmds.polyCube(), e=True,
                  forceElement=getSG(createShader('lambert')))


def initialize(load_plugins=True, load_MtoA=True, populate_scene=True):
    """Loads the development environment needed to
    test and build extensions for maya."""

    global app

    app = QtWidgets.QApplication([])
    standalone.initialize(name="python")

    if load_plugins:
        loadPlugins()
    if load_MtoA:
        initMtoa()
    if populate_scene:
        populateScene()
