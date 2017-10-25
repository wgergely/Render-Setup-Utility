import maya.cmds as cmds

class BatchShaderEditor(object):
    """
    This class provides a visual interface for batch-editing multiple shaders
    """

    aiStandard_Deafults = {
        'temp':"",
    }

    def __init__(self):
        pass



    def createUI(self):
        pass

    def resetUI(self):
        pass

    def updateUI(self):
        pass

    def _getValuesFromUI(self):

    def doIt(self):
        items = cmds.ls(selection=True, materials=True)

        for item in items:
            # Skip items that are not the specified type
            if cmds.objectType(item) != 'aiStandard':
                continue

            # aiStandard
            # Diffuse Color
            if not cmds.connectionInfo('%s.color' % item, isDestination=True):
                cmds.setAttr('%s.color' % item, 1,1,1, type="double3")
            # Diffuse Weight
            if not cmds.connectionInfo('%s.Kd' % item, isDestination=True):
                cmds.setAttr('%s.Kd' % item, 0.7)
            # Diffuse Roughness
            if not cmds.connectionInfo('%s.diffuseRoughness' % item, isDestination=True):
                cmds.setAttr('%s.diffuseRoughness' % item, 0.214)
            # Fresnel Affects Diffuse
            if not cmds.connectionInfo('%s.FresnelAffectDiff' % item, isDestination=True):
                cmds.setAttr('%s.FresnelAffectDiff' % item, 0)

            # Specular Color
            if not cmds.connectionInfo('%s.KsColor' % item, isDestination=True):
                cmds.setAttr('%s.KsColor' % item, 0.618,0.618,0.618, type="double3")
            # Specular Weight
            if not cmds.connectionInfo('%s.Ks' % item, isDestination=True):
                cmds.setAttr('%s.Ks' % item, 0.3)
            # Specular Roughness
            if not cmds.connectionInfo('%s.specularRoughness' % item, isDestination=True):
                cmds.setAttr('%s.specularRoughness' % item, 0.358)
            # Specular Fresnel
            if not cmds.connectionInfo('%s.specularFresnel' % item, isDestination=True):
                cmds.setAttr('%s.specularFresnel' % item, 1)
            # Specular Reflectance at Normal
            if not cmds.connectionInfo('%s.Ksn' % item, isDestination=True):
                cmds.setAttr('%s.Ksn' % item, 0.7)
