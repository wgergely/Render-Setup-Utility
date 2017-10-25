import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
import re

import RenderSetupUtility.main.utilities as util


# aiStandard has been depreciated in MtoA2 and repalced by aiStandard Surface
# mtoaVersion = cmds.pluginInfo('mtoa', query=True, version=True).split('.')[0]
mtoaVersion = 1

if float(mtoaVersion) == 1.0:
    SHADER_TYPES = (
        'aiStandard',
        'aiUtility',
        'aiAmbientOcclusion',
        'aiMotionVector',
        'aiShadowCatcher',
        'lambert',
        'aiRaySwitch',
        'aiSkin',
        'aiHair',
        'alSurface',
        'alLayer',
        'alCel',
        'alHair'
    )
if float(mtoaVersion) == 2.0:
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
    [0,'_oAllCnxs'], # Keep all connections
    [1,'_oNoCnxs'], # No connections
    [2, '_oColorOpacity'], # Keep color and opacity
    [3, '_oOpacity'],  # Keep opacity
    [4, '_oRed'],  # Flat red, keeps opacity
    [5, '_oGreen'],  # Flat green, keeps opacity
    [6, '_oBlue'],  # Flat blue, keeps opacity
    [7, '_oBlack'],  # Flat blue, keeps opacity
    [8, '_oWhite']  # Flat blue, keeps opacity
    # [9, '_oDuplicate']  # Flat blue, keeps opacity
)

SHADER_OVERRIDE_OPTIONS = (
    # {'ui':'Duplicate of Current',                 'type':None,            'mode':MODE[9][0], 'suffix':MODE[0][1]},
    # {'ui':'Custom',                               'type':None,            'mode':None,       'suffix':None},
    {'ui':'aiStandard - Keep All Connected Nodes','type':SHADER_TYPES[0], 'mode':MODE[0][0], 'suffix':MODE[0][1]},
    {'ui':'aiStandard - No Connections',          'type':SHADER_TYPES[0], 'mode':MODE[1][0], 'suffix':MODE[1][1]},
    {'ui':'aiStandard - Keep Opacity',            'type':SHADER_TYPES[0], 'mode':MODE[3][0], 'suffix':MODE[3][1]},
    {'ui':'aiUtility - Keep Color and Opacity',   'type':SHADER_TYPES[1], 'mode':MODE[2][0], 'suffix':MODE[2][1]},
    {'ui':'aiUtility - No Connections',           'type':SHADER_TYPES[1], 'mode':MODE[1][0], 'suffix':MODE[1][1]},
    {'ui':'aiUtility - Keep Opacity',             'type':SHADER_TYPES[1], 'mode':MODE[3][0], 'suffix':MODE[3][1]},
    {'ui':'aiUtility - RED - Keep Opacity',       'type':SHADER_TYPES[1], 'mode':MODE[4][0], 'suffix':MODE[4][1]},
    {'ui':'aiUtility - GREEN - Keep Opacity',     'type':SHADER_TYPES[1], 'mode':MODE[5][0], 'suffix':MODE[5][1]},
    {'ui':'aiUtility - BLUE - Keep Opacity',      'type':SHADER_TYPES[1], 'mode':MODE[6][0], 'suffix':MODE[6][1]},
    {'ui':'aiUtility - BLACK - Keep Opacity',     'type':SHADER_TYPES[1], 'mode':MODE[7][0], 'suffix':MODE[7][1]},
    {'ui':'aiUtility - WHITE - Keep Opacity',     'type':SHADER_TYPES[1], 'mode':MODE[8][0], 'suffix':MODE[8][1]},
    {'ui':'aiAmbientOcclusion - No Connections',  'type':SHADER_TYPES[2], 'mode':MODE[1][0], 'suffix':MODE[1][1]},
    {'ui':'aiAmbientOcclusion - Keep Opacity',    'type':SHADER_TYPES[2], 'mode':MODE[3][0], 'suffix':MODE[3][1]},
    {'ui':'aiMotionVector - No Connections',      'type':SHADER_TYPES[3], 'mode':MODE[1][0], 'suffix':MODE[1][1]},
    {'ui':'aiMotionVector - Keep Opacity',        'type':SHADER_TYPES[3], 'mode':MODE[3][0], 'suffix':MODE[3][1]},
    {'ui':'aiShadowCatcher - No Connections',     'type':SHADER_TYPES[4], 'mode':MODE[1][0], 'suffix':MODE[1][1]},
    {'ui':'aiShadowCatcher - Keep Opacity',       'type':SHADER_TYPES[4], 'mode':MODE[3][0], 'suffix':MODE[3][1]}
)

class ShaderUtility(object):
    '''
        Returns a shader list excluding override and meshes assigned to the shaders.
        Sets all data in to 'data' (dict).

        Provides utility methods for duplicating shaders.

        update() - Resets the 'data' dict.
    '''

    SOURCE_NODES = (
        'shadingEngine',
        'aiOption'
    )
    SHADER_NODES = (
        'shadingDependNode',
        'THdependNode'
    )
    # usedBy filter
    SURFACE_NODES = (
        'mesh',
        'nurbsSurface'
    )
    ENVIRONMENT_NODES = ( # from aiOption
        'aiRaySwitch',
        'aiPhysicalSky',
        'aiSky',
        'aiSkyDomeLight',
        'aiFog',
        'aiVolumeScattering'
    )

    def __init__(self):
        self.data = {}

        self.shaderList = self.getShaderList()
        self.overrides = None
        self.autoConnectShaders = None

        # Surface Shaders
        for shEngine in cmds.ls(type='shadingEngine'):
            if cmds.sets(shEngine, q=True) is None:
                continue
            shaderName = None
            for connection in [x for x in cmds.listConnections(shEngine)]:
                myType = cmds.nodeType(connection,i=True)
                if ('shadingDependNode' in myType or 'THdependNode' in myType):
                    if cmds.objectType(connection) in SHADER_TYPES:

                        # Check for namespace:
                        split = self.stripSuffix(connection).split(':')
                        if len(split) == 1: # no namespace
                            shaderName = split[0]
                            nameSpace = ''
                        if len(split) > 1:
                            shaderName = self.stripSuffix(connection).split(':')[-1]
                            nameSpace = self.stripSuffix(connection).split(':')[0]

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
                            'environment': False,
                            'standIn': False,
                            'autoConnect': None
                        }
            if shaderName is not None:
                for connection in cmds.sets(shEngine, q=True):
                    if cmds.ls(connection, long=True) != []:
                        self.data[shaderName]['usedBy'].append(cmds.ls(connection, long=True)[0])
                    self.data[shaderName]['count'] = len(self.data[shaderName]['usedBy'])

        # Environment nodes
        for item in cmds.ls(dagObjects=True, shapes=True, absoluteName=False, long=True):
                if cmds.nodeType(item) in self.ENVIRONMENT_NODES:

                    # Check for namespace:
                    split = str(item).split('|')[-1].split(':')
                    if len(split) == 1: # no namespace
                        shaderName = split[0]
                        nameSpace = ''
                    if len(split) > 1:
                        shaderName = shaderName = str(item).split('|')[-1].split(':')[-1]
                        nameSpace = shaderName = str(item).split('|')[-1].split(':')[0]

                    self.data['%s%s' % (nameSpace, shaderName)] = {
                        'name':shaderName,
                        'nameSpace': nameSpace,
                        'type': cmds.nodeType(item),
                        'usedBy': [shaderName],
                        'count': 1,
                        'shadingGroup': 'renderSettings',
                        'customString': '%s (1)' % shaderName,
                        'environment': True,
                        'standIn': False,
                        'autoConnect': None
                    }

        # StandIns
        for item in cmds.ls(type='aiStandIn'):
            # Check for namespace:
            split = str(item).split('|')[-1].split(':')
            if len(split) == 1: # no namespace
                shaderName = split[0]
                nameSpace = ''
            if len(split) > 1:
                shaderName = shaderName = str(item).split('|')[-1].split(':')[-1]
                nameSpace = shaderName = str(item).split('|')[-1].split(':')[0]

            self.data['%s%s' % (nameSpace, shaderName)] = {
                'name':shaderName,
                'nameSpace': nameSpace,
                'type': cmds.nodeType(item),
                'usedBy': [shaderName],
                'count': 1,
                'shadingGroup': 'renderSettings',
                'customString': '%s (1)' % shaderName,
                'environment': False,
                'standIn': True,
                'autoConnect': None
            }

    def update(self):
        self.__init__()

    def customStringToShaderName(self, string, properties=False):
        m = re.match('(.*\s+)([a-zA-Z0-9_:]+)(\s+)(.*)', string)
        if m is None:
            m = re.match('([a-zA-Z0-9_:]+)(\s+)(.*)', string)
            if m is None:
                print ('Couldn\'t get shader name from custom string.')
                return None
            else:
                if properties:
                    return m.group(3)
                else:
                    return m.group(1)
        else:
            if properties:
                return m.group(4)
            else:
                return m.group(2)
    def isActive(self, string):
        m = re.match('(.*\s+)([a-zA-Z0-9_:]+)(\s+)(.*)', string)
        if m is None:
            m = re.match('([a-zA-Z0-9_:]+)(\s+)(.*)', string)
            if m is None:
                return None
            else:
                return False
        else:
            return True
    def _getConnectedInputConnections(self, shaderName):
        # Check for namespaces:
        if cmds.objExists(':%s' % shaderName) is False:
            if cmds.objExists('*:%s' % shaderName) is True:
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
            plug = OpenMaya.MPlug( node, MFnDependencyNode.attribute(i) )
            # Check if the plug is an input and has a connection.
            # If does, push  [source, destination] to a list.
            if plug.isConnected and plug.isDestination:
                connections.append(
                    {'source':plug.source().partialName(includeNodeName=True, useLongNames=True),
                    'destination': plug.partialName(includeNodeName=True, useLongNames=True),
                    'destinationNode': shaderName,
                    'destinationAttribute': plug.partialName(useLongNames=True)}
                )
        return connections
    def copyShaderAttributes(self, shaderName, targetShader):
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
        connections = []

        def _transferValues(sourcePlug, destinationPlug):
            # Float Groups
            if apiType == OpenMaya.MFn.kAttribute3Float:
                for c in xrange(sourcePlug.numChildren()):
                    value = sourcePlug.child(c).asFloat()
                    destinationPlug.child(c).setFloat(value)
                    print sourcePlug.partialName(useLongNames=True)
                return

            # TYPED
            elif apiType == OpenMaya.MFn.kTypedAttribute:
                pType = OpenMaya.MFnTypedAttribute( pAttribute ).attrType()
                # String
                if pType == OpenMaya.MFnData.kString:
                    destinationPlug.setString(sourcePlug.asString())
                    return
            # NUMBERS
            if apiType == OpenMaya.MFn.kNumericAttribute:
                pType = OpenMaya.MFnNumericAttribute( pAttribute ).numericType()
                if pType == OpenMaya.MFnNumericData.kBoolean:
                    destinationPlug.setBool(sourcePlug.asBool())
                    return
                elif pType in [ OpenMaya.MFnNumericData.kShort, OpenMaya.MFnNumericData.kInt, OpenMaya.MFnNumericData.kLong, OpenMaya.MFnNumericData.kByte ]:
                    destinationPlug.setInt(sourcePlug.asInt())
                    print sourcePlug.asInt()
                    return
                elif pType in [ OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble, OpenMaya.MFnNumericData.kAddr ]:
                    destinationPlug.setDouble(sourcePlug.asDouble())
                    print sourcePlug.asDouble()
                    return
            # Enum
            elif apiType == OpenMaya.MFn.kEnumAttribute:
                destinationPlug.setInt(sourcePlug.asInt())
                print sourcePlug.asInt()
                return
        def _getValue(inPlug):
            # Float Groups - rotate, translate, scale; Compounds
            if apiType in [OpenMaya.MFn.kAttribute3Double, OpenMaya.MFn.kAttribute3Float, OpenMaya.MFn.kCompoundAttribute]:
                result = []
                if inPlug.isCompound:
                    for c in xrange(inPlug.numChildren()):
                        result.append(_getValue(inPlug.child(c)))
                    return result
            # Distance
            elif apiType in [ OpenMaya.MFn.kDoubleLinearAttribute, OpenMaya.MFn.kFloatLinearAttribute ]:
                return inPlug.asMDistance().asCentimeters()
            # Angle
            elif apiType in [ OpenMaya.MFn.kDoubleAngleAttribute, OpenMaya.MFn.kFloatAngleAttribute ]:
                return inPlug.asMAngle().asDegrees()
            # TYPED
            elif apiType == OpenMaya.MFn.kTypedAttribute:
                pType = OpenMaya.MFnTypedAttribute( pAttribute ).attrType()
                # Matrix
                if pType == OpenMaya.MFnData.kMatrix:
                    return OpenMaya.MFnMatrixData( inPlug.asMObject() ).matrix()
                # String
                elif pType == OpenMaya.MFnData.kString:
                    return inPlug.asString()
            # MATRIX
            elif apiType == OpenMaya.MFn.kMatrixAttribute:
                return OpenMaya.MFnMatrixData( inPlug.asMObject() ).matrix()
            # NUMBERS
            elif apiType == OpenMaya.MFn.kNumericAttribute:
                pType = OpenMaya.MFnNumericAttribute( pAttribute ).numericType()
                if pType == OpenMaya.MFnNumericData.kBoolean:
                    return inPlug.asBool()
                elif pType in [ OpenMaya.MFnNumericData.kShort, OpenMaya.MFnNumericData.kInt, OpenMaya.MFnNumericData.kLong, OpenMaya.MFnNumericData.kByte ]:
                    return inPlug.asInt()
                elif pType in [ OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble, OpenMaya.MFnNumericData.kAddr ]:
                    return inPlug.asDouble()
            # Enum
            elif apiType == OpenMaya.MFn.kEnumAttribute:
                return inPlug.asInt()

        for i in xrange(attributeCount):
            # Get plug from attribute
            sourcePlug = OpenMaya.MPlug(node, sourceMFnDependencyNode.attribute(i))
            destinationPlug = OpenMaya.MPlug(node, targetMFnDependencyNode.attribute(i))

            pAttribute = sourcePlug.attribute()
            apiType = sourcePlug.attribute().apiType()

            sourceAttr = '%s.%s'%(shaderName, sourcePlug.partialName(useLongNames=True))
            destAttr = '%s.%s'%(targetShader, sourcePlug.partialName(useLongNames=True))

            # FLOAT ARRAY
            if apiType == OpenMaya.MFn.kAttribute3Float:
                try:
                    attrType = cmds.getAttr(sourceAttr, type=True)
                    attrValue = cmds.getAttr(sourceAttr)[0]
                    cmds.setAttr(destAttr, attrValue[0], attrValue[1], attrValue[2], type=attrType)
                except:
                    pass
            # NUMBERS
            elif apiType == OpenMaya.MFn.kNumericAttribute:
                pType = OpenMaya.MFnNumericAttribute( pAttribute ).numericType()
                if pType == OpenMaya.MFnNumericData.kBoolean:
                    try:
                        attrValue = cmds.getAttr(sourceAttr)
                        cmds.setAttr(destAttr, attrValue)
                    except:
                        pass
                elif pType in [OpenMaya.MFnNumericData.kFloat, OpenMaya.MFnNumericData.kDouble]:
                    try:
                        attrValue = cmds.getAttr(sourceAttr)
                        cmds.setAttr(destAttr, attrValue)
                    except:
                        pass
            # ENUM
            elif apiType == OpenMaya.MFn.kEnumAttribute:
                try:
                    attrValue = cmds.getAttr(sourceAttr)
                    cmds.setAttr(destAttr, attrValue)
                except:
                    pass
            # TYPED
            elif apiType == OpenMaya.MFn.kTypedAttribute:
                pType = OpenMaya.MFnTypedAttribute( pAttribute ).attrType()
                if pType == OpenMaya.MFnData.kString:
                    try:
                        attrType = cmds.getAttr(sourceAttr, type=True)
                        attrValue = cmds.getAttr(sourceAttr)
                        cmds.setAttr(destAttr, attrValue, type=attrType)
                    except:
                        pass

    def duplicateShader(self, shaderName, choice=None, apply=True, isOverride=True):
        if apply is False:
            return

        if isOverride is True:
            OPTION = (item for item in SHADER_OVERRIDE_OPTIONS if item['ui'] == choice).next()
            if OPTION['type'] == SHADER_TYPES[1]:
                R = 'R'
            else:
                R = ''

            name = '%s%s_%s'%(shaderName, OPTION['suffix'], OPTION['type'])
        else:
            name = shaderName


        # Create new shader
        newShader = None
        if isOverride is True:
            if len(cmds.ls(name, materials=True)) != 0:
                newShader = name
            else:
                newShader = cmds.shadingNode(OPTION['type'], name=name, asShader=True)
        if isOverride is False:
            newShader = cmds.shadingNode(cmds.objectType(shaderName), name='%sDuplicate#'%(shaderName), asShader=True)

        connections = self._getConnectedInputConnections(shaderName)

        def _connect(cnx):
            source = connection['source']
            # float3 to float1 conversion
            if isOverride is True and (OPTION['type'] == SHADER_TYPES[1] or OPTION['type'] == SHADER_TYPES[2] or OPTION['type'] == SHADER_TYPES[3]) and connection['destinationAttribute'] == 'opacity':
                source = connection['source'] + R
            destination =  newShader + '.' + connection['destinationAttribute']
            if cmds.isConnected(source, destination) is False:
                cmds.connectAttr(source, destination, force=True)

        if isOverride is True:
            # Shader Default options
            if OPTION['mode'] == 0: # Keep all connections
                'Nothing to do here.'
            if OPTION['mode'] == 1: # No connections
                'Nothing to do here.'
            if OPTION['mode'] == 2: # Keep color and opacity
                'Nothing to do here.'
            if OPTION['mode'] == 3: # Keep opacity
                'Nothing to do here.'
            if OPTION['mode'] == 4: # Red, keep opacity
                cmds.setAttr(newShader + '.color', 1.0, 0.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 5: # Green, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 1.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 6: # Blue, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 0.0, 1.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 7: # Black, keep opacity
                cmds.setAttr(newShader + '.color', 0.0, 0.0, 0.0)
                cmds.setAttr(newShader + '.shadeMode', 2)
            if OPTION['mode'] == 8: # White, keep opacity
                cmds.setAttr(newShader + '.color', 1.0, 1.0, 1.0)
                cmds.setAttr(newShader + '.shadeMode', 2)

        # Shader connections
        for connection in connections:
            d = connection['destinationAttribute']

            if isOverride is False:
                _connect(connection)

            if isOverride is True:
                if OPTION['mode'] == 0: # Keep all connections
                    _connect(connection)
                if OPTION['mode'] == 1: # No connections
                    'Nothing to do here.'
                if OPTION['mode'] == 2: # Keep color and opacity
                    if d == 'color' or d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 3: # Keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 4: # Red, keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 5: # Green, keep opacity
                    if d == 'opacity':
                        _connect(connection)
                if OPTION['mode'] == 6: # Blue, keep opacity
                    if d == 'opacity':
                        _connect(connection)
        return newShader

    def getShaderGroups(self, excludeSolo=False):
        """Returns shader name groups."""

        matList = self.getShaderList(excludeUnused=False, excludeOverrides=True)

        d = {}
        for string in matList:
            if '_' in string:
                prefix, suffix = map(str.strip, str(string).split("_", 1))
                group = d.setdefault(prefix, [])
                group.append(suffix)

        dCopy = d.copy()
        if excludeSolo: # filters groups that have less 1 or less children
            for key in dCopy:
                if len(dCopy[key]) <= 1:
                    d.pop(key, None)
        return d

    def getShaderList(self, excludeOverrides=False, excludeUnused=False):
        arr = []
        matlist = [f.split(':')[-1] for f in cmds.ls(materials=True)]
        for item in matlist:
            if [f[1] for f in MODE if f[1] in item] != [] and excludeOverrides:
                continue # Exclude overrides
            if [f for f in self.data if item == self.data[f]['name'] and self.data[f]['usedBy']] == [] and excludeUnused:
                continue
            arr.append(item)
        self.shaderList = util.natsort(arr)
        return self.shaderList

    def stripSuffix(self, name):
        temp = 'xxx'
        idx = name.find('_')
        if idx == -1:
            return name

        # Replace basename temporarily
        basename = name[0:idx]
        suffixes = name[idx:]
        name = name.replace(basename, temp)

        filterByMode = [f for f in SHADER_OVERRIDE_OPTIONS if MODE[f['mode']][1] in name]
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
    def getMode(self, name):
        temp = 'xxx'
        idx = name.find('_')
        if idx == -1:
            return None

        # Replace basename temporarily
        basename = name[0:idx]
        suffixes = name[idx:]
        name = name.replace(basename, temp)

        filterByMode = [f for f in SHADER_OVERRIDE_OPTIONS if MODE[f['mode']][1] in name]
        filterByType = [f for f in filterByMode if f['type'] in name]

        for item in filterByType:
            return item
