script = """init = (function(){
    // Helper Functions
    function query(name){
        var m = name.match(/(.*)(_)(v\d{3})/);
        try{
            var subName = m[1]
            var newVersion = m[3]
        } catch(e) {
            var subName = name;
            var newVersion = null;
        }
        var q = {name:null,index:null,exists:null,parent:null,currentVersion:null,newVersion:null,needsUpdate:null}
        for (var i=1; i <= p.numItems; i++){
            if (newVersion != null){ // if in name contains a 'v###' element
                if( p.item(i).name.indexOf(subName) >= 0){
                    m = p.item(i).name.match(/(.*)(_)(v\d{3})/)
                    oldVersion = m[3]
                    // Compare versions
                    intOld = parseInt(oldVersion.replace(/\D/g,''), 10)
                    intNew = parseInt(newVersion.replace(/\D/g,''), 10)
                    q.currentVersion = oldVersion;
                    q.newVersion = newVersion;
                    if (intOld < intNew){
                        q.needsUpdate = true;
                    } else {
                        q.needsUpdate = false;
                    }
                    q.name = p.item(i).name;
                    q.index = i;
                    q.exists = true;
                    q.parent = p.item(i).parent;
                    return q;
                }
            }
            if (name == p.item(i).name){
                q.name = p.item(i).name;
                q.index = i;
                q.exists = true;
                q.parent = p.item(i).parent;
                return q;
            }
        }

        q.exists = false;
        return q;
    }
    // Code property of David Torno - https://www.provideocoalition.com/after-effects-extendscript-training-ep-15/
    function removeKeyframes(propertyInput){
    	if(propertyInput instanceof Property){
    		while(propertyInput.numKeys > 0){
    			propertyInput.removeKey(1);
    		}
    	}
    }
    function transferKeyframes(propertyInput, keysAry){
    	if(propertyInput instanceof Property && keysAry instanceof Array){
            var keysAryLength, newKeyTime, addNewKey, newKeyIndex;
            keysAryLength = keysAry.length;
            for(var k = 0; k < keysAryLength; k++){
                addNewKey = propertyInput.addKey(keysAry[k].curKeyTime);
                newKeyIndex = addNewKey;
                propertyInput.setValueAtKey(newKeyIndex, keysAry[k].curKeyValue);
                if(keysAry[k].outIn != KeyframeInterpolationType.HOLD){
                    propertyInput.setTemporalEaseAtKey(newKeyIndex, keysAry[k].ie, keysAry[k].oe);
                }
                propertyInput.setInterpolationTypeAtKey(newKeyIndex, keysAry[k].inIn, keysAry[k].outIn);
                if((keysAry[k].inIn == KeyframeInterpolationType.BEZIER) && (keysAry[k].outIn == KeyframeInterpolationType.BEZIER)){
                    propertyInput.setTemporalContinuousAtKey(newKeyIndex, keysAry[k].cb);
                    propertyInput.setTemporalAutoBezierAtKey(newKeyIndex, keysAry[k].ab);
                }
                if((propertyInput.propertyValueType == PropertyValueType.TwoD_SPATIAL) || (propertyInput.propertyValueType == PropertyValueType.ThreeD_SPATIAL)){
                    propertyInput.setSpatialContinuousAtKey(newKeyIndex, keysAry[k].scb);
                    propertyInput.setSpatialAutoBezierAtKey(newKeyIndex, keysAry[k].sab);
                    propertyInput.setSpatialTangentsAtKey(newKeyIndex, keysAry[k].ist, keysAry[k].ost);
                }
            }
            if((propertyInput.propertyValueType == PropertyValueType.TwoD_SPATIAL) || (propertyInput.propertyValueType == PropertyValueType.ThreeD_SPATIAL)){
                for(var r = 0; r < keysAryLength; r++){
                    propertyInput.setRovingAtKey((r+1), keysAry[r].rov);
                }
            }
            return true;
    	}
    }
    function collectKeyframes(propertyInput){
    	if(propertyInput instanceof Property){
    		var totalKeys, prop, keyIndexList, curKeyIndex, curKeyValue, inIn, outIn, ab, cb, ie, oe, sab, scb, ist, ost, rov, twoDS, threeDS;
    		twoDS = PropertyValueType.TwoD_SPATIAL;
    		threeDS = PropertyValueType.ThreeD_SPATIAL;
    		keyIndexList = new Array();
    		totalKeys = propertyInput.numKeys;
    		if(totalKeys > 0){
    			for(var i = 1; i <= totalKeys; i++){
    				curKeyTime = propertyInput.keyTime(i);
    				curKeyIndex = i;
    				curKeyValue = propertyInput.keyValue(i);
    				inIn = propertyInput.keyInInterpolationType(curKeyIndex);
    				outIn = propertyInput.keyOutInterpolationType(curKeyIndex);
    				if(inIn == KeyframeInterpolationType.BEZIER && outIn == KeyframeInterpolationType.BEZIER){
    					ab = propertyInput.keyTemporalAutoBezier(curKeyIndex);
    					cb = propertyInput.keyTemporalContinuous(curKeyIndex);
    				}
    				if(inIn != KeyframeInterpolationType.HOLD || outIn != KeyframeInterpolationType.HOLD){
    					ie = propertyInput.keyInTemporalEase(curKeyIndex);
    					oe = propertyInput.keyOutTemporalEase(curKeyIndex);
    				}
    				if(propertyInput.propertyValueType == twoDS || propertyInput.propertyValueType == threeDS){
    					sab = propertyInput.keySpatialAutoBezier(curKeyIndex);
    					scb = propertyInput.keySpatialContinuous(curKeyIndex);
    					ist = propertyInput.keyInSpatialTangent(curKeyIndex);
    					ost = propertyInput.keyOutSpatialTangent(curKeyIndex);
    					rov = propertyInput.keyRoving(curKeyIndex);
    				}
    				keyIndexList[keyIndexList.length] = {
    					'curKeyTime':curKeyTime,
    					'curKeyIndex':curKeyIndex,
    					'curKeyValue':curKeyValue,
    					'inIn':inIn,
    					'outIn':outIn,
    					'ab':ab,
    					'cb':cb,
    					'ie':ie,
    					'oe':oe,
    					'sab':sab,
    					'scb':scb,
    					'ist':ist,
    					'ost':ost,
    					'rov':rov
    					}
    			}
    			return keyIndexList;
    		}else{
    			return null;
    		}
    	}
    }
    function getAllMayaCameras(){
        q = []
        info = {compIndex:null,layerIndex:null}
         for (var i=1; i <= p.numItems; i++){
             if (p.item(i).typeName === 'Composition'){
                 layers = p.item(i).layers
                 for (var j=0; j < layers.length; j++){
                     lyr = p.item(i).layer(j+1)
                     // Filter by layer type and name.
                    if (lyr instanceof CameraLayer && lyr.name ==  MAYA_CAMERA_NAME){
                        q.push({compIndex:i,layerIndex:j+1})
                    }
                 }
             }
         }
        return q
    }
    function updateCameras(){
        cams = getAllMayaCameras()
        source = null;
        for (var i=0; i < cams.length; i++){
            if (p.item(cams[i].compIndex).name === MAYA_CAMERA_COMP){
                source = p.item(cams[i].compIndex).layer(cams[i].layerIndex);
                break
            }
        }
        if (source != null){
            //Properties
            var sPos = source.property('ADBE Transform Group').property('Position'),
                sRotX = source.property('ADBE Transform Group').property('X Rotation'),
                sRotY = source.property('ADBE Transform Group').property('Y Rotation'),
                sRotZ = source.property('ADBE Transform Group').property('Z Rotation'),
                sOri = source.property('ADBE Transform Group').property('Orientation'),
                sScale = source.property('ADBE Transform Group').property('Scale'),
                sZoom = source.property('Camera Options').property('Zoom'),
                sDoF = source.property('Camera Options').property('Depth of Field'),
                sFocusDistance = source.property('Camera Options').property('Focus Distance'),
                sAperture = source.property('Camera Options').property('Aperture'),
                sBlurLevel = source.property('Camera Options').property('Blur Level');


            var sPosKeys = collectKeyframes(sPos),
                sRotXKeys = collectKeyframes(sRotX),
                sRotYKeys = collectKeyframes(sRotY),
                sRotZKeys = collectKeyframes(sRotZ),
                sOriKeys = collectKeyframes(sOri),
                sScaleKeys = collectKeyframes(sScale),
                sZoomKeys = collectKeyframes(sZoom),
                sDoFKeys = collectKeyframes(sDoF),
                sFocusDistanceKeys = collectKeyframes(sFocusDistance),
                sApertureKeys = collectKeyframes(sAperture),
                sBlurLevelKeys = collectKeyframes(sBlurLevel);

            // Transfer all camera properties from source to all other cameras
            for (var i=0; i < cams.length; i++){
                if (p.item(cams[i].compIndex).name !== MAYA_CAMERA_COMP){
                    camera = p.item(cams[i].compIndex).layer(cams[i].layerIndex);
                    var prop = null;

                    prop = camera.property('ADBE Transform Group').property('Position');
                    if (sPosKeys != null){
                       removeKeyframes(prop)
                       transferKeyframes(prop,sPosKeys)
                    } else {
                       prop.setValue(sPos.value)
                    }

                    prop = camera.property('ADBE Transform Group').property('X Rotation');
                    if (sRotXKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sRotXKeys)
                    } else {
                        prop.setValue(sRotX.value)
                    }

                    prop = camera.property('ADBE Transform Group').property('Y Rotation');
                    if (sRotYKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sRotYKeys)
                    } else {
                        prop.setValue(sRotY.value)
                    }

                    prop = camera.property('ADBE Transform Group').property('Z Rotation');
                    if (sRotZKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sRotZKeys)
                    } else {
                        prop.setValue(sRotZ.value)
                    }

                    prop = camera.property('ADBE Transform Group').property('Orientation');
                    if (sOriKeys != null){
                        removeKeyframes(prop.value)
                        transferKeyframes(prop,sOriKeys)
                    } else {
                        prop.setValue(sOri.value)
                    }

                    // !SCALE IS NOT IMPLEMENTED!

                    prop = camera.property('Camera Options').property('Zoom');
                    if (sZoomKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sZoomKeys)
                    } else {
                        prop.setValue(sZoom.value)
                    }

                    prop = camera.property('Camera Options').property('Depth of Field');
                    if (sDoFKeys != null){
                        removeKeyframes(prop)
                       transferKeyframes(prop,sDoFKeys)
                    } else {
                        prop.setValue(sDoF.value)
                    }

                    prop = camera.property('Camera Options').property('Focus Distance');
                    if (sFocusDistanceKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sFocusDistanceKeys)
                    } else {
                       prop.setValue(sFocusDistance.value)
                    }

                    prop = camera.property('Camera Options').property('Aperture');
                    if (sApertureKeys != null){
                        removeKeyframes(prop)
                        transferKeyframes(prop,sApertureKeys)
                    } else {
                        prop.setValue(sAperture.value)
                    }

                    prop = camera.property('Camera Options').property('Blur Level');
                    if (sBlurLevelKeys != null){
                       removeKeyframes(prop)
                       transferKeyframes(prop,sBlurLevelKeys)
                    } else {
                        prop.setValue(sBlurLevel.value)
                    }
                }
            }
        }
    }
    // http://stackoverflow.com/questions/1916218/find-the-longest-common-starting-substring-in-a-set-of-strings
    function sharedStart(array){
        var A= array.concat().sort(),
        a1= A[0], a2= A[A.length-1], L= a1.length, i= 0;
        while(i<L && a1.charAt(i)=== a2.charAt(i)) i++;
        return a1.substring(0, i);
    }


    //GLOBALS
    MAYA_CAMERA_NAME = '_MayaCamera_Shape'
    MAYA_CAMERA_COMP = '_MayaCamera_'

    var p = app.project;

    // Set frame start to 1, to match Maya.
    p.displayStartFrame = 1;

    var name = '<Name>' + '_precomp',
      width = <Width>,
      height = <Height>,
      pixelAspect = <Pixel_Aspect>,
      duration = <Duration>,
      frameRate = <Frame_Rate>;
      imagePaths = <Image_Paths>,
      mayaCameraPath = '<Maya_Camera>',
      io = null,
      item = null,
      COMP = null;


    //If item exists with a similar name, rename to latest version.
    var sh=null, oldName=null;
    for (var i=1; i <= p.numItems; i++){
        oldName = app.project.item(i).name
        sh = sharedStart([oldName, name]);
        if (sh){
            app.project.item(i).name = name;
            break
        }
    }
    item = query(name);
    if (item.exists == false){
        COMP = p.items.addComp(name, width, height, pixelAspect, duration, frameRate);
    } else {
        COMP = p.item(item.index)
        COMP.width = width;
        COMP.height = height;
        COMP.pixelAspect = pixelAspect;
        COMP.duration = duration;
        COMP.frameRate = frameRate;
    }

    var elementsFolder;
    item = query('Elements');
    if ( item.exists == false){
        elementsFolder = app.project.items.addFolder('Elements');
    } else {
        elementsFolder = p.item(item.index);
    }

    // Render Layers
    for (var i = 0; i < imagePaths.length; i++){
      io = new ImportOptions(File(imagePaths[i]));
      if (io.canImportAs(ImportAsType.FOOTAGE)){
          io.importAs = ImportAsType.FOOTAGE;
      }
      item = query(<Footage_Names>[i]);
      if (item.exists == false) {
          io.sequence = true;
          footage = p.importFile(io);
          footage.mainSource.conformFrameRate = frameRate;
          footage.name = <Footage_Names>[i];
      } else {
        if (item.needsUpdate){
            footage = p.item(item.index);
            io = new ImportOptions(p.item(item.index).file);
            if (io.canImportAs(ImportAsType.FOOTAGE)){
                io.importAs = ImportAsType.FOOTAGE;
            }
            io.sequence = true;
            duplicate = p.importFile(io);
            footage.replaceWithSequence(File(imagePaths[i]), true);
            footage.mainSource.reload();
            footage.mainSource.conformFrameRate = frameRate;
            footage.mainSource.pixelAspect = pixelAspect;
            footage.name = <Footage_Names>[i];
        } else {
            footage = p.item(item.index);
            footage.mainSource.reload();
            footage.mainSource.conformFrameRate = frameRate;
            footage.pixelAspect = pixelAspect;
        }
      }
    }

    // =======================================
    // CAMERA

    //Import Maya camera from file

    item = query(MAYA_CAMERA_COMP)
    io = new ImportOptions(File(mayaCameraPath))
    if (item.exists === false){
        footage = p.importFile(io);
    } else {
        p.item(item.index).remove()
        footage = p.importFile(io);
    }

    // Iterate through all cameras and propagate properties from source camera.

    updateCameras()

    //Feedback
    alert('Sucessfully imported new footage items.', 'Maya AutoConnect')
})()"""
