"""
Module doc stub.
"""

import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.collection as collection
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.selector as selector
import maya.cmds as cmds
import RenderSetupUtility.main.shaderUtility as shaderUtility


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


LAYER_SUFFIX = '_rsLayer'
COLLECTION_SUFFIX = '_collection'
EMPTY_COLLECTION = '_untitled_'
LIGHTS_ON = 'lights_on'
LIGHTS_OFF = 'lights_off'
TEMP_NAME = '_tempMeshShape'

"""
Override attributes
"""
OVERRIDE_ATTRIBUTES = (
    {
        'long': 'primaryVisibility',
        'short': 'vis',
        'nice': 'Visible in Camera',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('prim-', '')
    },
    {
        'long': 'aiVisibleInDiffuseReflection',
        'short': 'ai_visr',
        'nice': 'Visible in Diffuse Reflection',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('dr-', '')
    },
    {
        'long': 'aiVisibleInDiffuseTransmission',
        'short': 'ai_vidt',
        'nice': 'Visible in Diffuse Transmission',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('dt-', '')
    },
    {
        'long': 'aiVisibleInSpecularReflection',
        'short': 'ai_visr',
        'nice': 'Visible in Specular Reflection',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('sr-', '')
    },
    {
        'long': 'aiVisibleInSpecularTransmission',
        'short': 'ai_vist',
        'nice': 'Visible in Specular Transmission',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('st-', '')
    },
    {
        'long': 'aiVisibleInVolume',
        'short': 'ai_viv',
        'nice': 'Visible in Volume',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('v-', '')
    },
    {
        'long': 'visibleInReflections',
        'short': 'vir',
        'nice': 'Visible in Reflections',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('rl-', '')
    },
    {
        'long': 'visibleInRefractions',
        'short': 'vif',
        'nice': 'Visible in Refractions',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('rr-', '')
    },
    {
        'long': 'aiOpaque',
        'short': 'ai_opaque',
        'nice': 'Opaque',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('', 'tr-')
    },
    {
        'long': 'castsShadows',
        'short': 'csh',
        'nice': 'Cast Shadows',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('cs-', '')
    },
    {
        'long': 'receiveShadows',
        'short': 'rcsh',
        'nice': 'Recieve Shadows',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('rs-', '')
    },
    {
        'long': 'aiSelfShadows',
        'short': 'ai_self_shadows',
        'nice': 'Cast Self Shadows',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('ss-', '')
    },
    {
        'long': 'doubleSided',
        'short': 'ds',
        'nice': 'Double Sided',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': True,
        'custom': ('ds-', '')
    },
    {
        'long': 'aiMatte',
        'short': 'ai_matte',
        'nice': 'Matte',
        'type': OpenMaya.MFnNumericData.kBoolean,
        'default': False,
        'custom': ('M-', '')
    }
)


class Utility(object):
    '''
    Wrapper class for Render Setup manipulations.
    '''

    def __init__(self):

        self.activeLayer = None
        self.activeCollection = None

        self.defaultLayer = renderSetup.instance().getDefaultRenderLayer()
        self.defaultName = self.defaultLayer.name()

        self.overrideAttributes = OVERRIDE_ATTRIBUTES

        def addLayer(inName):
            lyrs = renderSetup.instance().getRenderLayers()

            if isinstance(inName, basestring):
                for lyr in lyrs:
                    if lyr.name() == inName:
                        print('# {0} exists already. Skipping.'.format(inName))
                        self._extendActiveLayer(lyr, valid=True)
                        return self.activeLayer
                l = renderSetup.instance().createRenderLayer(inName)
                self._extendActiveLayer(l, valid=True)

                self.switchLayer(inName)

                lr = l.renderSettingsCollectionInstance()
                la = l.aovCollectionInstance()
                ll = l.lightsCollectionInstance()

                c = l.createCollection(EMPTY_COLLECTION)
                c.setSelfEnabled(False)
                sel = c.getSelector()
                sel.setPattern('*')
                sel.setFilterType(0)

                self._extendActiveCollection(c, valid=True)

                return self.activeLayer

        def switchLayer(inValue, switchLayer=False):
            lyrs = renderSetup.instance().getRenderLayers()

            if inValue == self.defaultName:
                l = renderSetup.instance().getDefaultRenderLayer()
                if switchLayer:
                    renderSetup.instance().switchToLayer(l)
                self._extendActiveLayer(l, valid=True)
                return self.activeLayer
            else:
                if isinstance(inValue, basestring):
                    l = renderSetup.instance().getRenderLayer(inValue)
                    if switchLayer:
                        renderSetup.instance().switchToLayer(l)
                    self._extendActiveLayer(l, valid=True)
                    return self.activeLayer
                elif type(inValue) is int:
                    l = lyrs[inValue]
                    if switchLayer:
                        renderSetup.instance().switchToLayer(l)
                    self._extendActiveLayer(l, valid=True)
                    return self.activeLayer

        def _collection(inValue=None, isQuery=False, addOverrides=True):
            """
            Private convenience function called via activeLayer.collection(string or None)
            """

            if self.activeLayer.name() == self.defaultName:
                self._extendActiveCollection(valid=False)
                return self.activeCollection

            colls = self.activeLayer.getCollections()

            if inValue is None:
                self._extendActiveCollection(valid=False)
                return colls

            # Find collection in the current layer

            found = [c for c in colls if '{0}{1}'.format(
                inValue, COLLECTION_SUFFIX) in c.name()]

            if found != []:
                self._extendActiveCollection(inCollection=found[0], valid=True)
                return self.activeCollection

            if found == [] and isQuery is True:
                self._extendActiveCollection(valid=False)
                return self.activeCollection

            if found == [] and isQuery is False:
                return self.addCollection('{0}{1}'.format(inValue, COLLECTION_SUFFIX), addOverrides=addOverrides)
                return self.activeCollection

        def addCollection(inValue, addOverrides=True):
            '''
            Adds a new collection and the default overrides.
            '''

            l = self.activeLayer
            colls = l.getCollections()
            if isinstance(inValue, basestring):
                # Check for existing collection with
                for coll in colls:
                    if coll.name() == inValue:
                        print('# Collection \'' + coll.name() +
                              '\' already exists in \'' + self.activeLayer.name() + '\'')
                        return None
                c = l.createCollection(inValue)
                self._extendActiveCollection(c, valid=True)

                # Add overrides
                if addOverrides is True:
                    self._addArnoldPropertyOverrides()
                return self.activeCollection
            if type(inValue) is list or tuple:
                for string in inValue:
                    for item in colls:
                        exists = False
                        if item.name() == string:
                            exists = True
                            print('# Collection \'' + item.name() +
                                  '\' already exists in \'' + self.activeLayer.name() + '\'')
                            break
                    if exists is False:
                        c = l.createCollection(string)
                        self._extendActiveCollection(c, valid=True)
                        self._addArnoldPropertyOverrides()
                return self.activeCollection

        def removeCollection(inValue):
            """
            Get and delete collection by name.
            Checks for incremented maya object names.
            """

            colls = self.activeLayer.getCollections()

            found = [c for c in colls if inValue in c.name()]

            if found != []:
                collection.delete(found[0])
                return True

            if found == []:
                print('# Couldn\'t find collection to delete.')
                return False

        def setSelection(inValue, inFilterType):
            # 0 = All, 1 = Transforms, 2 = Shapes, 4 = Lights, 7 = Cameras
            self.activeCollection.getSelector().setFilterType(inFilterType)
            self.activeCollection.selection.set(inValue)

        def removeSelection(inValue):
            self.activeCollection.selection.remove(s)

        def overrides(inValue=None):
            if self.activeCollection is None:
                return None
            if self.activeLayer is None:
                return None

            ov = self.activeCollection.getOverrides()

            # Return whole list
            if inValue is None:
                return ov
            # Return by index
            if type(inValue) is int:
                try:
                    return ov[inValue]
                except:
                    print('# Couldn\'t get override of that index.')
                    return None
            # Return by name
            if isinstance(inValue, basestring):
                found = False
                for o in ov:
                    try:
                        if o.attributeName() == inValue:
                            found = True
                            return o
                    except:
                        print('# Couldn\'t get override based on that name.')
                if found is False:
                    return None

        def setOverrideValue(inName, inValue=None):
            ov = self.activeCollection.overrides()

            for o in ov:
                try:
                    if o.attributeName() == inName:
                        o.setAttrValue(inValue)
                except:
                    print('# Couldn\'t set override attribute value.')
                    return None

        def getOverrideValue(inName):
            ov = self.activeCollection.overrides()
            for o in ov:
                try:
                    if o.attributeName() == inName:
                        return o.getAttrValue()
                except:
                    print('# Couldn\'t get override attribute value.')
                    return None

        def _extendActiveLayer(inLayer=None, valid=True):
            if inLayer.name() == self.defaultName:
                self.activeLayer = self.defaultLayer
                self.activeLayer.switchLayer = switchLayer
                self.activeLayer.addLayer = addLayer
                self.activeLayer.collection = None
                self.activeLayer.addCollection = None
                self.activeLayer.removeCollection = None
            if valid is True:
                self.activeLayer = inLayer
                self.activeLayer.switchLayer = switchLayer
                self.activeLayer.addLayer = addLayer
                self.activeLayer.collection = _collection
                self.activeLayer.addCollection = addCollection
                self.activeLayer.removeCollection = removeCollection
            else:
                self.activeLayer = None
            return self.activeLayer

        def _extendActiveCollection(inCollection=None, valid=True):
            if valid:
                self.activeCollection = inCollection
                self.activeCollection.overrides = overrides
                self.activeCollection.setOverrideValue = setOverrideValue
                self.activeCollection.getOverrideValue = getOverrideValue
                self.activeCollection.setSelection = setSelection
                self.activeCollection.removeSelection = removeSelection
                self.activeCollection.selection = inCollection.getSelector().staticSelection
                self.activeCollection.layer = self.activeLayer
            else:
                self.activeCollection = None

        def _addArnoldAOVOverrides():
            '''
            Adds a list of aov overrides for Arnold rendering.
            '''

            # Add overrides
            try:
                for index, item in enumerate(self.overrideAttributes):
                    attr = self.overrideAttributes[index]['long']
                    value = self.overrideAttributes[index]['default']

                    o = self.activeCollection.createOverride(
                        '%s#' % (attr), 'absOverride')
                    o.finalize('%s.%s' % (TEMP_NAME, attr))
                    o.setAttrValue(value)
                    self.activeCollection.overrides = overrides
            except:
                self.activeCollection.overrides = overrides
                raise RuntimeError(
                    'An error occured adding default overrides.')

            if cmds.objExists(TEMP_NAME):
                p = cmds.listRelatives(TEMP_NAME, allParents=True)[0]
                cmds.delete(p)

        def _addArnoldPropertyOverrides():
            '''
            Adds a list of absolute overrides of Arnold properties.
            '''

            # Add temp polyObject
            if cmds.objExists(TEMP_NAME):
                pass
            else:
                OpenMaya.MFnDagNode().create('mesh', name=TEMP_NAME)
            # Add overrides
            try:
                for index, item in enumerate(self.overrideAttributes):
                    attr = self.overrideAttributes[index]['long']
                    value = self.overrideAttributes[index]['default']

                    o = self.activeCollection.createOverride(
                        '%s#' % (attr), 'absOverride')
                    o.finalize('%s.%s' % (TEMP_NAME, attr))
                    o.setAttrValue(value)
                    self.activeCollection.overrides = overrides
            except:
                self.activeCollection.overrides = overrides
                print('# An error occured adding default overrides.')

            if cmds.objExists(TEMP_NAME):
                p = cmds.listRelatives(TEMP_NAME, allParents=True)[0]
                cmds.delete(p)

        def _addShaderOverride():
            '''
            Adds a ShaderOverride to the activeCollection.
            '''
            SHADER_OVERRIDE_DEFAULTNAME = '%sShaderOverride#' % self.activeCollection.name()
            o = self.activeCollection.createOverride(
                SHADER_OVERRIDE_DEFAULTNAME, 'shaderOverride')
            return o

        self._extendActiveLayer = _extendActiveLayer
        self._extendActiveCollection = _extendActiveCollection
        self._addArnoldPropertyOverrides = _addArnoldPropertyOverrides

        self.addShaderOverride = _addShaderOverride

        self.addLayer = addLayer
        self.switchLayer = switchLayer
        self.collection = _collection
        self.addCollection = addCollection
        self.removeCollection = removeCollection
        self.setSelection = setSelection
        self.removeSelection = removeSelection
        self.overrides = overrides

        # Set activeLayer on init
        self._extendActiveLayer(
            renderSetup.instance().getVisibleRenderLayer(), valid=True)
    # Methods

    def removeMissingSelections(self):
        lyrs = renderSetup.instance().getRenderLayers()
        for l in lyrs:
            cl = l.getCollections()
            for c in cl:
                if c.typeName() == 'collection':
                    selector = c.getSelector()
                    items = selector.staticSelection.asList()
                    validList = []
                    if selector.hasMissingObjects():
                        for item in items:
                            if cmds.objExists(item):
                                validList.append(item)
                            selector.staticSelection.set(validList)

    def layer(self, inValue=None):
        lyrs = renderSetup.instance().getRenderLayers()
        if inValue is None:
            self._extendActiveLayer(valid=False)
            print('# layer(): No index or name given.')
            return self.activeLayer
        # Return by index
        if type(inValue) is int:
            try:
                self._extendActiveLayer(lyrs[inValue], valid=True)
                return self.activeLayer
            except:
                self._extendActiveLayer(inLayer=None, valid=False)
                print('# Couldn\'t get render layer of that index.')
                return self.activeLayer
        # Return by name
        if isinstance(inValue, basestring):
            inValue += LAYER_SUFFIX
            found = False
            for l in lyrs:
                if l.name() == inValue:
                    found = True
                    self._extendActiveLayer(l, valid=True)
                    return self.activeLayer
            if found is False:
                self.addLayer(inValue)
                return self.activeLayer

    def layers(self):
        return renderSetup.instance().getRenderLayers()
