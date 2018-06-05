import maya.api.OpenMaya as OpenMaya

ARNOLD_PROPERTIES = (
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


SHADER_TYPES = (
    'aiStandardSurface',
    'aiUtility',
    'aiToon',
    'aiAmbientOcclusion',
    'aiMotionVector',
    'aiShadowMatte',
    'aiRaySwitch',
    'aiSkin',
    'aiHair',
    'lambert',
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
        'nice': 'aiStandardSurface - Keep All Connected Nodes',
        'type': SHADER_TYPES[0],
        'mode': MODE[0][0],
        'suffix': MODE[0][1]
    },
    {
        'nice': 'aiStandardSurface - No Connections',
        'type': SHADER_TYPES[0],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiToon - No Connections',
        'type': SHADER_TYPES[0],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiStandardSurface - Keep Opacity',
        'type': SHADER_TYPES[0],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'nice': 'aiUtility - Keep Color and Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[2][0],
        'suffix': MODE[2][1]
    },
    {
        'nice': 'aiUtility - No Connections',
        'type': SHADER_TYPES[1],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiUtility - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'nice': 'aiUtility - RED - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[4][0],
        'suffix': MODE[4][1]
    },
    {
        'nice': 'aiUtility - GREEN - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[5][0],
        'suffix': MODE[5][1]
    },
    {
        'nice': 'aiUtility - BLUE - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[6][0],
        'suffix': MODE[6][1]
    },
    {
        'nice': 'aiUtility - BLACK - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[7][0],
        'suffix': MODE[7][1]
    },
    {
        'nice': 'aiUtility - WHITE - Keep Opacity',
        'type': SHADER_TYPES[1],
        'mode': MODE[8][0],
        'suffix': MODE[8][1]
    },
    {
        'nice': 'aiAmbientOcclusion - No Connections',
        'type': SHADER_TYPES[2],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiAmbientOcclusion - Keep Opacity',
        'type': SHADER_TYPES[2],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'nice': 'aiMotionVector - No Connections',
        'type': SHADER_TYPES[3],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiMotionVector - Keep Opacity',
        'type': SHADER_TYPES[3],
        'mode': MODE[3][0],
        'suffix': MODE[3][1]
    },
    {
        'nice': 'aiShadowCatcher - No Connections',
        'type': SHADER_TYPES[4],
        'mode': MODE[1][0],
        'suffix': MODE[1][1]
    },
    {
        'nice': 'aiShadowCatcher - Keep Opacity',
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
