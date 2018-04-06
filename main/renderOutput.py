"""
This module defines resolution presets and methods
that apply them to the Maya output and camera settings.
"""

import os
import re

import maya.cmds as cmds
import RenderSetupUtility.main.utilities as util

# pylint: disable=C0103

windowID = 'RenderSetupUtilityWindow'

OUTPUT_TEMPLATES = (
    'Not set',
    '<RenderLayer>\\<Version>\\<RenderLayer>_<Version>',
    '<RenderLayer>\\<RenderLayer>_<Version>',
    '<RenderLayer>\\<Version>\\<RenderLayer>'
)

""" Resolution templates.
#TODO: this should probably come from config file.
"""
SIZE_TEMPLATE = (
    {
        'ui': 'HD 1080*0.5 - 1.778:1',
        'width': 960,
        'height': 540,
        'suffix': '540'
    },
    {
        'ui': 'HD 1080*1 - 1.778:1',
        'width': 1920,
        'height': 1080,
        'suffix': '1080'
    },
    {
        'ui': 'HD 1080*1.5 - 1.778:1',
        'width': 2880,
        'height': 1620,
        'suffix': '1620'
    },
    {
        'ui': 'ULTRAHD - 1.778:1',
        'width': 3840,
        'height': 2160,
        'suffix': 'ultraHD'
    },
    {
        'ui': 'DCI2K - 1.90:1',
        'width': 2048,
        'height': 1080,
        'suffix': 'dci2k'
    },
    {
        'ui': 'DCI4K - 1.90:1',
        'width': 4096,
        'height': 2160,
        'suffix': 'dci4k'
    },
    {
        'ui': 'Cinema Widescreen - 2.35:1',
        'width': 1920,
        'height': 818,
        'suffix': '235'
    },
    {
        'ui': 'Cinema Widescreen - 1.85:1',
        'width': 1920,
        'height': 1038,
        'suffix': '185'
    },
    {
        'ui': 'Styleframe - 1.667:1 - 1k',
        'width': 1000,
        'height': 600,
        'suffix': 'styleframe'
    },
    {
        'ui': 'Styleframe - 1.667:1 - 2k',
        'width': 2000,
        'height': 1200,
        'suffix': 'styleframe'
    },
    {
        'ui': 'Styleframe - 1.667:1 - 5k',
        'width': 5000,
        'height': 3000,
        'suffix': 'styleframe'
    },
    {
        'ui': 'A4 200dpi - Landscape',
        'width': 2339,
        'height': 1654,
        'suffix': 'a4200l'
    },
    {
        'ui': 'A4 200dpi - Vertical',
        'width': 1654,
        'height': 2339,
        'suffix': 'a4200v'
    },
    {
        'ui': 'A4 300dpi - Landscape',
        'width': 3508,
        'height': 2480,
        'suffix': 'a4300l'
    },
    {
        'ui': 'A4 300dpi - Vertical',
        'width': 2480,
        'height': 3508,
        'suffix': 'a4300v'
    },
    {
        'ui': 'Square 1k - 1:1',
        'width': 1024,
        'height': 1024,
        'suffix': 'sq1k'
    },
    {
        'ui': 'Square 2k - 1:1',
        'width': 2048,
        'height': 2048,
        'suffix': 'sq2k'
    },
    {
        'ui': 'Square 4k - 1:1',
        'width': 4096,
        'height': 4096,
        'suffix': 'sq4k'
    },
    {
        'ui': 'Square 6k - 1:1',
        'width': 6144,
        'height': 6144,
        'suffix': 'sq6k'
    },
    {
        'ui': 'Square 8k - 1:1',
        'width': 8192,
        'height': 8192,
        'suffix': 'sq8k'
    },
)

TIME_TEMPLATE = (
    {
        'ui': '15 fps (game)',
        'name': 'game',
        'fps': 15
    },
    {
        'ui': '24 fps (film)',
        'name': 'film',
        'fps': 24
    },
    {
        'ui': '25 fps (pal)',
        'name': 'pal',
        'fps': 25
    },
    {
        'ui': '30 fps (ntsc)',
        'name': 'ntsc',
        'fps': 30
    },
    {
        'ui': '48 fps (show)',
        'name': 'show',
        'fps': 48
    },
    {
        'ui': '50 fps (palf)',
        'name': 'palf',
        'fps': 50
    },
    {
        'ui': '60 fps (ntscf)',
        'name': 'ntscf',
        'fps': 60
    },
)

DEFAULTS_NODE = 'defaultRenderGlobals'
RESOLUTION_NODE = 'defaultResolution'


class RenderOutput(object):
    """
    """

    def __init__(self):
        self.defaultTemplate = OUTPUT_TEMPLATES[1]
        self.currentTemplate = None
        self.defaultImageSize = OUTPUT_TEMPLATES[1]
        self.currentImageSize = OUTPUT_TEMPLATES[1]

    @staticmethod
    def setTemplate(template):
        """ Apply the given template to the
        """

        if template == OUTPUT_TEMPLATES[0]:
            cmds.setAttr('{}.imageFilePrefix'.format(
                DEFAULTS_NODE), '', type='string')
        else:
            cmds.setAttr('{}.renderVersion'.format(
                DEFAULTS_NODE), type='string')
            cmds.setAttr('{}.extensionPadding'.format(DEFAULTS_NODE), 4)
            cmds.setAttr('{}.animation'.format(DEFAULTS_NODE), 1)
            cmds.setAttr('{}.putFrameBeforeExt'.format(DEFAULTS_NODE), 1)
            cmds.setAttr('{}.periodInExt'.format(DEFAULTS_NODE), 2)
            cmds.setAttr('{}.useFrameExt'.format(DEFAULTS_NODE), 0)
            cmds.setAttr('{}.outFormatControl'.format(DEFAULTS_NODE), 0)
            cmds.setAttr('{}.imageFilePrefix'.format(
                DEFAULTS_NODE), template, type='string')
            cmds.setAttr('{}.imageFormat'.format(DEFAULTS_NODE), 8)
            cmds.setAttr('perspShape.renderable', 0)

            if cmds.objExists('camera'):
                cmds.setAttr('cameraShape.renderable', 1)


    def setVersion(self, version):
        cmds.setAttr('%s.renderVersion ' %
                     DEFAULTS_NODE, version, type='string')

    def incrementVersion(self):
        pass

    def _getAOVs(self):
        "Get all aovs"

        AOV_BEAUTY = 'beauty'
        AOV_LIST = [AOV_BEAUTY]

        for node in cmds.ls(type='aiAOV'):
            AOV_LIST.append(str(cmds.getAttr('%s.name' % node)))

        return AOV_LIST

    def pathStr(self, renderLayer, long=False):
        ROOT = cmds.workspace(query=True, rootDirectory=True)
        IMAGES = 'images'
        version = cmds.optionMenu('%s_optionMenu04' %
                                  (windowID), query=True, value=True)
        if ROOT:
            self.currentTemplate = cmds.getAttr(
                '%s.imageFilePrefix' % DEFAULTS_NODE)
            if self.currentTemplate:
                if [t for t in OUTPUT_TEMPLATES if self.currentTemplate == t]:

                    t = self.currentTemplate

                    if cmds.getAttr("defaultArnoldDriver.mergeAOVs") is False:
                        # When merge aovs is turned off the aovs are added to a separate folder.
                        # This needs to be accounted for

                        substr = t.find('\\<RenderLayer>')

                        tBase = t[0:substr]
                        tTail = t[substr:]
                        tAOV = '<AOV>'

                        t = '%s\\%s%s' % (tBase, tAOV, tTail)

                    path = t.replace('<RenderLayer>', renderLayer).replace(
                        '<Version>', version)

                    if long is False:
                        return path
                    if long:
                        longName = os.path.join(ROOT, IMAGES, path)
                        longName = os.path.normpath(longName)
                        return longName
                else:
                    return None
            else:
                return None

    def getVersions(self, lyr):
        ROOT = cmds.workspace(query=True, rootDirectory=True)
        IMAGES = 'images'
        if ROOT:
            path = os.path.normpath(os.path.join(ROOT, IMAGES, lyr))
            if os.path.isdir(path):
                versions = [d for d in os.listdir(path) if os.path.isdir(
                    os.path.join(path, d)) and re.match('^v\d{3}$', d)]
                return util.natsort(versions)
            else:
                return None
        else:
            print 'Workgroup isn\'t set.'
            return None

    def addVersionDir(self, lyr, version):
        ROOT = cmds.workspace(query=True, rootDirectory=True)
        if ROOT:
            IMAGES = 'images'
            path = os.path.normpath(os.path.join(ROOT, IMAGES, lyr))
            if os.path.isdir(path):
                versionFolder = os.path.normpath(os.path.join(path, version))
                if not os.path.exists(versionFolder):
                    os.makedirs(versionFolder)
                    print 'New version folder added.'
        else:
            print 'Workgroup isn\'t set.'

    def setStartFrame(self, frame=1):
        frame = round(frame, 0)
        currentFrame = round(cmds.currentTime(query=True))

        cmds.playbackOptions(animationStartTime=int(frame))
        cmds.playbackOptions(minTime=int(frame))
        if currentFrame < frame:
            cmds.currentTime(frame, edit=True)
        else:
            cmds.currentTime(currentFrame, edit=True)

    def setEndFrame(self, frame=250):
        frame = round(frame, 0)
        currentFrame = round(cmds.currentTime(query=True))

        cmds.playbackOptions(animationStartTime=int(frame))
        cmds.playbackOptions(minTime=int(frame))
        if currentFrame < frame:
            cmds.currentTime(frame, edit=True)
        else:
            cmds.currentTime(currentFrame, edit=True)
