"""
Module defines the shader utility:
it collects information about the shaders and thei assignment
used in the current maya scene.
"""

# pylint: disable=C0103

import re

import maya.api.OpenMaya as OpenMaya  # pylint: disable=E0401
import maya.cmds as cmds  # pylint: disable=E0401
import RenderSetupUtility.main.utilities as util

SHADER_TYPES = (
    'aiStandardSurface',
    'aiUtility',
    'aiAmbientOcclusion',
    'aiMotionVector',
    'aiShadowMatte',
    'aiStandard',
    'lambert',
    'aiRaySwitch',
    'aiSkin',
    'aiHair',
    'alSurface',
    'alLayer',
    'alCel',
    'alHair'
)

MODE = (
    [0, '_oAllCnxs'],  # Keep all connections
    [1, '_oNoCnxs'],  # No connections
    [2, '_oColorOpacity'],  # Keep color and opacity
    [3, '_oOpacity'],  # Keep opacity
    [4, '_oRed'],  # Flat red, keeps opacity
    [5, '_oGreen'],  # Flat green, keeps opacity
    [6, '_oBlue'],  # Flat blue, keeps opacity
    [7, '_oBlack'],  # Flat blue, keeps opacity
    [8, '_oWhite']  # Flat blue, keeps opacity
)

SHADER_OVERRIDE_OPTIONS = (
    {
        'ui': 'aiStandardSurface - Keep All Connected Nodes',
        'type': SHADER_TYPES[0],
        'mode': MODE[0][0],
        'suffix': MODE[0][1]
    },
    {
        'ui': 'aiStandardSurface - No Connections',
        'type': SHADER_TYPES[0],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'ui': 'aiStandardSurface - Keep Opacity',
        'type': SHADER_TYPES[0],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'ui': 'aiUtility - Keep Color and Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[2][0],
        'suffix': MODE[2][1]
    },
    {
        'ui': 'aiUtility - No Connections',
        'type': SHADER_TYPES[1],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'ui': 'aiUtility - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'ui': 'aiUtility - RED - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[4][0],
        'suffix': MODE[4][1]
    },
    {
        'ui': 'aiUtility - GREEN - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[5][0],
        'suffix': MODE[5][1]
    },
    {
        'ui': 'aiUtility - BLUE - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[6][0],
        'suffix': MODE[6][1]
    },
    {
        'ui': 'aiUtility - BLACK - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[7][0],
        'suffix': MODE[7][1]
    },
    {
        'ui': 'aiUtility - WHITE - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[8][0],
        'suffix': MODE[8][1]
    },
    {
        'ui': 'aiAmbientOcclusion - No Connections',
        'type': SHADER_TYPES[2],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'ui': 'aiAmbientOcclusion - Keep Opacity',
        'type': SHADER_TYPES[2],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'ui': 'aiMotionVector - No Connections',
        'type': SHADER_TYPES[3],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'ui': 'aiMotionVector - Keep Opacity',
        'type': SHADER_TYPES[3],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'ui': 'aiShadowCatcher - No Connections',
        'type': SHADER_TYPES[4],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'ui': 'aiShadowCatcher - Keep Opacity',
        'type': SHADER_TYPES[4],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
)

SOURCE_NODES = (
    'shadingEngine',
    'aiOption'
)

SHADER_NODES = (
    'shadingDependNode',
    'THdependNode'
)

SURFACE_NODES = (
    'mesh',
    'nurbsSurface'
)

ENVIRONMENT_NODES = (
    'aiRaySwitch',
    'aiPhysicalSky',
    'aiSky',
    'aiSkyDomeLight',
    'aiFog',
    'aiVolumeScattering'
)

LIGHT_NODES = (
    'aiAreaLight',
    'aiSkyDomeLight',
    'aiMeshLight',
    'aiSky',
    'aiPhotometricLight',
    'aiLightPortal',
    'directionalLight',
    'pointLight',
    'spotLight',
    'areaLight'
)


class Singleton(type):
    """
    Define an Instance operation that lets clients access its unique
    instance.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ShaderUtility(object):
    '''
        Singleton class containing a shader list and assignments
        excluding override shadersself.

        Sets all data in to 'data' (dict).
        Provides utility methods for duplicating shaders.

        update() - Resets the 'data' dict.
    '''

    __metaclass__ = Singleton

    def __init__(self):
        self.data = {}
        self.shaderList = self.getShaderList(excludeOverrides=True)
        self.overrides = None
        self.autoConnectShaders = None
        self.update()

    def _setShadersToData(self):
        """ Collects scene shaders
        """

        shapes = cmds.ls(dagObjects=True, shapes=True, long=True)

        # iterate over shading engines
        for shEngine in cmds.ls(type='shadingEngine'):
            if cmds.sets(shEngine, q=True) is None:
                continue

            shaderName = None
            for connection in [x for x in cmds.listConnections(shEngine)]:
                if [f for f in SHADER_NODES if f in cmds.nodeType(connection, i=True)]:
                    if cmds.objectType(connection) not in SHADER_TYPES:
                        continue

                    # Check for namespace:
                    split = self.stripSuffix(connection).split(':')
                    if len(split) == 1:  # no namespace
                        shaderName = split[0]
                        nameSpace = ''
                    if len(split) > 1:
                        shaderName = self.stripSuffix(
                            connection).split(':')[-1]
                        nameSpace = self.stripSuffix(
                            connection).split(':')[0]
                    if len(nameSpace) >= 1:
                        shaderName = '%s:%s' % (nameSpace, shaderName)

                    self.data[shaderName] = {
                        'name': shaderName,
                        'nameSpace': nameSpace,
                        'type': cmds.objectType(connection),
                        'usedBy': [],
                        'count': 0,
                        'shadingGroup': shEngine,
                        'customString': '',
                        'shader': True,
                        'environment': False,
                        'standIn': False,
                        'light': False,
                        'autoConnect': False
                    }

                    for sh_connection in cmds.sets(shEngine, q=True):
                        if not cmds.ls(sh_connection, long=True):
                            continue
                        self.data[shaderName]['usedBy'].append(
                            cmds.ls(sh_connection, long=True)[0]
                        )
                        self.data[shaderName]['count'] = len(
                            self.data[shaderName]['usedBy']
                        )

    def _setEnvironmentsToData(self):
        """ Collects scene environments
        """

        shapes = cmds.ls(dagObjects=True, shapes=True, long=True)
        for item in [f for f in shapes if cmds.nodeType(f) in ENVIRONMENT_NODES]:
            # Checking for namespace:
            split = str(item).split('|')[-1].split(':')
            if len(split) == 1:  # no namespace
                shaderName = split[0]
                nameSpace = ''
            if len(split) > 1:
                nameSpace = shaderName = str(item).split('|')[-1].split(':')[0]
                shaderName = shaderName = str(
                    item).split('|')[-1].split(':')[-1]
            if len(nameSpace) >= 1:
                shaderName = '%s:%s' % (nameSpace, shaderName)

            self.data[shaderName] = {
                'name': shaderName,
                'nameSpace': nameSpace,
                'type': cmds.nodeType(item),
                'usedBy': [cmds.ls(shaderName, long=True)[0]],
                'count': 1,
                'shadingGroup': 'renderSettings',
                'customString': '%s (1)' % shaderName,
                'shader': False,
                'environment': True,
                'standIn': False,
                'light': False,
                'autoConnect': False
            }

    def _setStandinsToData(self):
        """ Collects scene environments
        """
        # StandIns
        for item in cmds.ls(type='aiStandIn'):

            # Checking for namespace:
            split = str(item).split('|')[-1].split(':')
            if len(split) == 1:  # no namespace
                shaderName = split[0]
                nameSpace = ''
            if len(split) > 1:
                nameSpace = shaderName = str(item).split('|')[-1].split(':')[0]
                shaderName = shaderName = str(
                    item).split('|')[-1].split(':')[-1]
            if len(nameSpace) >= 1:
                shaderName = '%s:%s' % (nameSpace, shaderName)

            self.data[shaderName] = {
                'name': shaderName,
                'nameSpace': nameSpace,
                'type': cmds.nodeType(item),
                'usedBy': [cmds.ls(shaderName, long=True)[0]],
                'count': 1,
                'shadingGroup': 'renderSettings',
                'customString': '%s (1)' % shaderName,
                'shader': False,
                'environment': False,
                'standIn': True,
                'light': False,
                'autoConnect': False
            }

    def _setLightsToData(self):
        """ Collects scene environments
        """

        shapes = cmds.ls(dagObjects=True, shapes=True, long=True)
        # Lights
        for item in [f for f in shapes if cmds.nodeType(f) in LIGHT_NODES]:

            # Checking for namespace:
            split = str(item).split('|')[-1].split(':')
            if len(split) == 1:  # no namespace
                shaderName = split[0]
                nameSpace = ''
            if len(split) > 1:
                nameSpace = shaderName = str(item).split('|')[-1].split(':')[0]
                shaderName = shaderName = str(
                    item).split('|')[-1].split(':')[-1]
            if len(nameSpace) >= 1:
                shaderName = '%s:%s' % (nameSpace, shaderName)

            self.data[shaderName] = {
                'name': shaderName,
                'nameSpace': nameSpace,
                'type': cmds.nodeType(item),
                'usedBy': [cmds.ls(shaderName, long=True)[0]],
                'count': 1,
                'shadingGroup': 'renderSettings',
                'customString': '%s (1)' % shaderName,
                'shader': False,
                'environment': False,
                'standIn': False,
                'light': True,
                'autoConnect': False
            }

    def update(self):
        """ Populate self.data
        """
        self.data = {}
        self._setShadersToData()
        self._setEnvironmentsToData()
        self._setStandinsToData()
        self._setLightsToData()

    @staticmethod
    def customStringToShaderName(string, properties=False):
        """ Get the shader's name from a custom string
        """
        m = re.match(r'(.*\s+)([a-zA-Z0-9_:]+)(\s+)(.*)', string)
        if m is None:
            m = re.match(r'([a-zA-Z0-9_:]+)(\s+)(.*)', string)
            if m is None:
                print '# Couldn\'t get shader name from custom string.'
                return None
            if properties:
                return m.group(3)
            return m.group(1)
        else:
            if properties:
                return m.group(4)
            return m.group(2)

    @staticmethod
    def isActive(string):
        """ Check if the shader is active
        """
        m = re.match(r'(.*\s+)([a-zA-Z0-9_:]+)(\s+)(.*)', string)
        if m is None:
            m = re.match(r'([a-zA-Z0-9_:]+)(\s+)(.*)', string)
            if m is None:
                return None
            return False
        else:
            return True

    @staticmethod
    def _getConnectedInputConnections(shaderName):
        """ List all the input connection of a given shader,
        that has active connections.
        """

        if cmds.objExists(':%s' % shaderName) is False:
            if cmds.objExists('*:%s' % shaderName):
                shaderName = '*:%s' % shaderName
            else:
                raise RuntimeError('Shader %s couldn\'t be found.')

        if cmds.ls(shaderName, materials=True) == 0:
            return None
        sel = OpenMaya.MSelectionList().add(shaderName)
        node = sel.getDependNode(0)
        MFnDependencyNode = OpenMaya.MFnDependencyNode(node)
        # Cycle through all attributes
        attributeCount = int(MFnDependencyNode.attributeCount())

        connections = []
        for i in xrange(attributeCount):
            # Get plug from attribute
            plug = OpenMaya.MPlug(node, MFnDependencyNode.attribute(i))
            # Check if the plug is an input and has a connection.
            # If does, push  [source, destination] to a list.
            if plug.isConnected and plug.isDestination:
                connections.append(
                    {'source': plug.source().partialName(includeNodeName=True, useLongNames=True),
                     'destination': plug.partialName(includeNodeName=True, useLongNames=True),
                     'destinationNode': shaderName,
                     'destinationAttribute': plug.partialName(useLongNames=True)}
                )
        return connections

    @staticmethod
    def _connectPlug(sourcePlug, destinationPlug):
        pAttribute = sourcePlug.attribute()
        apiType = sourcePlug.attribute().apiType()

        # Float Groups
        if apiType == OpenMaya.MFn.kAttribute3Float:
            for c in xrange(sourcePlug.numChildren()):
                value = sourcePlug.child(c).asFloat()
                destinationPlug.child(c).setFloat(value)
            return

        # TYPED
        elif apiType == OpenMaya.MFn.kTypedAttribute:
            pType = OpenMaya.MFnTypedAttribute(pAttribute).attrType()
            # String
            if pType == OpenMaya.MFnData.kString:
                destinationPlug.setString(sourcePlug.asString())
                return
        # NUMBERS
        if apiType == OpenMaya.MFn.kNumericAttribute:
            pType = OpenMaya.MFnNumericAttribute(pAttribute).numericType()
            if pType == OpenMaya.MFnNumericData.kBoolean:
                destinationPlug.setBool(sourcePlug.asBool())
                return
            elif pType in [
                    OpenMaya.MFnNumericData.kShort,
                    OpenMaya.MFnNumericData.kInt,
                    OpenMaya.MFnNumericData.kLong,
                    OpenMaya.MFnNumericData.kByte
            ]:
                destinationPlug.setInt(sourcePlug.asInt())
                return
            elif pType in [
                    OpenMaya.MFnNumericData.kFloat,
                    OpenMaya.MFnNumericData.kDouble,
                    OpenMaya.MFnNumericData.kAddr
            ]:
                destinationPlug.setDouble(sourcePlug.asDouble())
                return
        # Enum
        elif apiType == OpenMaya.MFn.kEnumAttribute:
            destinationPlug.setInt(sourcePlug.asInt())
            return

    def _getPlugValue(self, inPlug):
        apiType = inPlug.attribute().apiType()
        pAttribute = inPlug.attribute()

        # Float Groups - rotate, translate, scale; Compounds
        if apiType in [
                OpenMaya.MFn.kAttribute3Double,
                OpenMaya.MFn.kAttribute3Float,
                OpenMaya.MFn.kCompoundAttribute
        ]:
            result = []
            if inPlug.isCompound:
                for c in xrange(inPlug.numChildren()):
                    result.append(self._getPlugValue(inPlug.child(c)))
                return result
        # Distance
        elif apiType in [OpenMaya.MFn.kDoubleLinearAttribute, OpenMaya.MFn.kFloatLinearAttribute]:
            return inPlug.asMDistance().asCentimeters()
        # Angle
        elif apiType in [OpenMaya.MFn.kDoubleAngleAttribute, OpenMaya.MFn.kFloatAngleAttribute]:
            return inPlug.asMAngle().asDegrees()
        # TYPED
        elif apiType == OpenMaya.MFn.kTypedAttribute:
            pType = OpenMaya.MFnTypedAttribute(pAttribute).attrType()
            # Matrix
            if pType == OpenMaya.MFnData.kMatrix:
                return OpenMaya.MFnMatrixData(inPlug.asMObject()).matrix()
            # String
            elif pType == OpenMaya.MFnData.kString:
                return inPlug.asString()
        # MATRIX
        elif apiType == OpenMaya.MFn.kMatrixAttribute:
            return OpenMaya.MFnMatrixData(inPlug.asMObject()).matrix()
        # NUMBERS
        elif apiType == OpenMaya.MFn.kNumericAttribute:
            pType = OpenMaya.MFnNumericAttribute(pAttribute).numericType()
            if pType == OpenMaya.MFnNumericData.kBoolean:
                return inPlug.asBool()
            elif pType in [OpenMaya.MFnNumericData.kShort, OpenMaya.MFnNumericData.kInt, OpenMaya.MFnNumericData.kLong, OpenMaya.MFnNumericData.kByte]:
                return inPlug.asInt()
            elif pType in [OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble, OpenMaya.MFnNumericData.kAddr]:
                return inPlug.asDouble()
        # Enum
        elif apiType == OpenMaya.MFn.kEnumAttribute:
            return inPlug.asInt()

    @staticmethod
    def transferShaderAttributes(shaderName, targetShader):
        """ Copies shader attributes when duplicateing a shader
        """

        if cmds.ls(shaderName, materials=True) == 0:
            return None

        sel = OpenMaya.MSelectionList().add(shaderName)
        node = sel.getDependNode(0)
        sourceMFnDependencyNode = OpenMaya.MFnDependencyNode(node)

        sel = OpenMaya.MSelectionList().add(targetShader)
        node = sel.getDependNode(0)
        targetMFnDependencyNode = OpenMaya.MFnDependencyNode(node)

        # Cycle through all attributes
        attributeCount = int(sourceMFnDependencyNode.attributeCount())

        for i in xrange(attributeCount):
            # Get plug from attribute
            sourcePlug = OpenMaya.MPlug(
                node, sourceMFnDependencyNode.attribute(i))
            destinationPlug = OpenMaya.MPlug(
                node, targetMFnDependencyNode.attribute(i))

            pAttribute = sourcePlug.attribute()
            apiType = sourcePlug.attribute().apiType()

            sourceAttr = '%s.%s' % (
                shaderName, sourcePlug.partialName(useLongNames=True))
            destAttr = '%s.%s' % (
                targetShader, sourcePlug.partialName(useLongNames=True))

            # FLOAT ARRAY
            if apiType == OpenMaya.MFn.kAttribute3Float:
                attrType = cmds.getAttr(sourceAttr, type=True)
                attrValue = cmds.getAttr(sourceAttr)
                cmds.setAttr(
                    destAttr, attrValue[0], attrValue[1], attrValue[2], type=attrType)
            # NUMBERS
            elif apiType == OpenMaya.MFn.kNumericAttribute:
                pType = OpenMaya.MFnNumericAttribute(pAttribute).numericType()
                if pType == OpenMaya.MFnNumericData.kBoolean:
                    attrValue = cmds.getAttr(sourceAttr)
                    cmds.setAttr(destAttr, attrValue)
                elif pType in [OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble]:
                    attrValue = cmds.getAttr(sourceAttr)
                    cmds.setAttr(destAttr, attrValue)
            # ENUM
            elif apiType == OpenMaya.MFn.kEnumAttribute:
                attrValue = cmds.getAttr(sourceAttr)
                cmds.setAttr(destAttr, attrValue)
            # TYPED
            elif apiType == OpenMaya.MFn.kTypedAttribute:
                pType = OpenMaya.MFnTypedAttribute(pAttribute).attrType()
                if pType == OpenMaya.MFnData.kString:
                    attrType = cmds.getAttr(sourceAttr, type=True)
                    attrValue = cmds.getAttr(sourceAttr)
                    cmds.setAttr(destAttr, attrValue, type=attrType)

    def duplicateShader(self, shaderName, choice=None, applyOp=True, isOverride=True):
        """ Duplicate shader
        """

        if applyOp is False:
            return

        if isOverride is True:
            OPTION = (
                item for item in SHADER_OVERRIDE_OPTIONS if item['ui'] == choice).next()
            if OPTION['type'] == SHADER_TYPES[1]:
                R = 'R'
            else:
                R = ''

            name = '%s%s_%s' % (shaderName, OPTION['suffix'], OPTION['type'])
        else:
            name = shaderName

        # Create new shader
        newShader = None
        if isOverride is True:
            if cmds.ls(name, materials=True):
                newShader = name
            else:
                newShader = cmds.shadingNode(
                    OPTION['type'], name=name, asShader=True)

        if isOverride is False:
            newShader = cmds.shadingNode(cmds.objectType(
                shaderName), name='%sDuplicate#' % (shaderName), asShader=True)

        connections = self._getConnectedInputConnections(shaderName)

        def _connect(cnx):
            source = cnx['source']
            # float3 to float1 conversion
            if isOverride is True and (
                    OPTION['type'] == SHADER_TYPES[1] or
                    OPTION['type'] == SHADER_TYPES[2] or
                    OPTION['type'] == SHADER_TYPES[3]
                ) and (
                    cnx['destinationAttribute'] == 'opacity'
                ):
                source = cnx['source'] + R

            destination = newShader + '.' + cnx['destinationAttribute']
            if cmds.isConnected(source, destination) is False:
                cmds.connectAttr(source, destination, force=True)

        if isOverride is True:
            # Shader Default options
            if OPTION['mode'] == 0:  # Keep all connections
                pass
            if OPTION['mode'] == 1:  # No connections
                pass
            if OPTION['mode'] == 2:  # Keep color and opacity
                pass
            if OPTION['mode'] == 3:  # Keep opacity
                pass
            if OPTION['mode'] == 4:  # Red, keep opacity
                cmds.setAttr(newShader + '.color', 1.0, 0.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 5:  # Green, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 1.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 6:  # Blue, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 0.0, 1.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 7:  # Black, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 0.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 8:  # White, keep opacity
                cmds.setAttr(newShader + '.color', 1.0, 1.0, 1.0)
                cmds.setAttr(newShader + '.shadeMode', 2)

        # Shader connections
        for connection in connections:
            d = connection['destinationAttribute']

            if isOverride is False:
                _connect(connection)

            if isOverride is True:
                if OPTION['mode'] == 0:  # Keep all connections
                    _connect(connection)
                if OPTION['mode'] == 1:  # No connections
                    pass
                if OPTION['mode'] == 2:  # Keep color and opacity
                    if d == 'color' or d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 3:  # Keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 4:  # Red, keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 5:  # Green, keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 6:  # Blue, keep opacity
                    if d == 'opacity':
                        _connect(connection)
        return newShader

    def getShaderGroups(self, excludeSolo=False):
        """Returns shader name groups"""

        d = {}

        # Empty
        group = d.setdefault('', [])
        group.append('')

        for shaderName in self.data:
            if self.data[shaderName]['light']:
                group = d.setdefault('<Lights>', [])
                group.append(shaderName)
            if self.data[shaderName]['environment']:
                group = d.setdefault('<Environment>', [])
                group.append(shaderName)
            if self.data[shaderName]['shader']:
                group = d.setdefault('<Shaders>', [])
                group.append(shaderName)
            if self.data[shaderName]['standIn']:
                group = d.setdefault('<StandIns>', [])
                group.append(shaderName)

        # Shaders
        for string in self.data:
            if '_' in string:
                prefix, suffix = map(str.strip, str(string).split("_", 1))
                group = d.setdefault(prefix, [])
                group.append(suffix)

        dCopy = d.copy()
        if excludeSolo:  # filters groups that have less 1 or less children
            for key in dCopy:
                if len(dCopy[key]) <= 1:
                    d.pop(key, None)
        return d

    def getShaderList(self, excludeOverrides=False, excludeUnused=False):
        arr = []
        matlist = [f.split(':')[-1] for f in cmds.ls(materials=True)]
        for item in matlist:
            if [f[1] for f in MODE if f[1] in item] != [] and excludeOverrides:
                continue  # Exclude overrides
            if [f for f in self.data if item == self.data[f]['name'] and self.data[f]['usedBy']] == [] and excludeUnused:
                continue
            arr.append(item)
        self.shaderList = util.natsort(arr)

        return self.shaderList

    @staticmethod
    def stripSuffix(name):
        temp = 'xxx'
        idx = name.find('_')
        if idx == -1:
            return name

        # Replace basename temporarily
        basename = name[0:idx]
        name = name.replace(basename, temp)

        filterByMode = [
            f for f in SHADER_OVERRIDE_OPTIONS if MODE[f['mode']][1] in name]
        filterByType = [f for f in filterByMode if f['type'] in name]

        if filterByType:
            for item in filterByType:
                return name.replace(
                    temp, basename
                ).replace(
                    MODE[item['mode']][1], str()
                ).replace(
                    '_%s' % (item['type']), str()
                )
        else:
            for item in filterByMode:
                return name.replace(
                    temp, basename
                ).replace(
                    MODE[item['mode']][1], str()
                )

        return name.replace(
            temp, basename
        )

    @staticmethod
    def getMode(name):
        temp = 'xxx'
        idx = name.find('_')
        if idx == -1:
            return None

        # Replace basename temporarily
        basename = name[0:idx]
        name = name.replace(basename, temp)

        filterByMode = [
            f for f in SHADER_OVERRIDE_OPTIONS if MODE[f['mode']][1] in name]
        filterByType = [f for f in filterByMode if f['type'] in name]

        for item in filterByType:
            return item
