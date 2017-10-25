init = (function(){
    var UVS_LAYER = 'uvs';
    var UVS_STATE = true;
    try{
        d = app.activeDocument;
    } catch(e) {
        d = null;
    }
    if (d){
        lyrs = d.layers
        for (var i=0; i < lyrs.length; i++){
            if (lyrs[i].name == UVS_LAYER){
               UVS_LAYER = d.layers[i];
               UVS_STATE = UVS_LAYER.visible;
               UVS_LAYER.visible = false;
               break
            }
        }
    }
    ui = new CreateUI()
    ui.show()
    UVS_LAYER.visible = UVS_STATE;
})()


function CreateUI(Object) {

	ATTRIBUTE_TYPES = [{attribute:'color', type: 'float3', name: 'Diffuse Color'},
        {attribute:'Kd', type: 'float1', name: 'Diffuse Color Weight'},
        {attribute:'diffuseRoughness', type: 'float1', name: 'Diffuse Roughness'},
        {attribute:'directDiffuse', type: 'float1', name: 'Direct Diffuse Weight'},
        {attribute:'indirectDiffuse', type: 'float1', name: 'Indirect Diffuse Weight'},
        {attribute:'KsColor', type: 'float3', name: 'Specular Color'},
        {attribute:'Ks', type: 'float1', name: 'Specular Weight'},
        {attribute:'specularRoughness', type: 'float1', name: 'Specular Roughness'},
        {attribute:'specularAnisotropy', type: 'float1', name: 'Specular Anisotropy'},
        {attribute:'specularRotation', type: 'float1' , name: 'Specular Rotation'},
        {attribute:'KrColor', type: 'float3', name: 'Reflection Color'},
        {attribute:'Kr', type: 'float1', name: 'Reflection Weight'},
        {attribute:'KtColor', type: 'float3', name: 'Refraction Color'},
        {attribute:'Kt', type: 'float1', name: 'Refraction Weight'},
        {attribute:'emissionColor', type: 'float3', name: 'Emission Color'},
        {attribute:'opacity', type: 'float3', name: 'Opacity'}];

	TYPES = [
		'.png',
		'.jpg'
	];

	MAKETX_PATH = 'C:\\solidangle\\mtoadeploy\\2017\\bin\\maketx.exe'

	var self = this;
	var listItem = [];
	for (var i = 0; i < ATTRIBUTE_TYPES.length; i++) {
		listItem.push(ATTRIBUTE_TYPES[i] .name)
	}
	this.window = new Window('dialog', 'Export as Preset');
	this.window.orientation = 'column';
	this.window.alignment = 'right';
	//add drop-down
	this.window.DDgroup = this.window.add('group');
	this.window.DDgroup.orientation = 'row';
	this.window.DDgroup.add('statictext', undefined, "Export as:");
	this.window.DDgroup.DD = this.window.DDgroup.add('dropdownlist', undefined, undefined, {items:listItem})
	this.window.DDgroup.DD2 = this.window.DDgroup.add('dropdownlist', undefined, undefined, {items:TYPES})
	this.window.DDgroup.DD.selection = 0;
	this.window.DDgroup.DD2.selection = 0;
	this.window.closeBtn = this.window.add('button', undefined, 'OK');
	// add button functions
	this.window.closeBtn.onClick = function() {
		var selection1 = String(self.window.DDgroup.DD.selection);
		var selection2  = String(self.window.DDgroup.DD2.selection);
		var activeDocument = null;
		var parentPath = null;
		var documentName = null;
		try {
			activeDocument = app.activeDocument;
			parentPath = app.activeDocument.path;
			for (var i = 0; i < ATTRIBUTE_TYPES.length; i++){
				if (ATTRIBUTE_TYPES[i].name != selection1) {
					continue;
				} else{
					attributeName = ATTRIBUTE_TYPES[i].attribute;
				}
			}
			if (selection2 == TYPES[0]){
				options = new ExportOptionsSaveForWeb();
				options.quality = 100;
				options.format = SaveDocumentType. PNG;
				options.PNG8 = false;
				options.transparency = true;
			}
			if (selection2 == TYPES[1]){
				options = new ExportOptionsSaveForWeb();
				options.quality = 100;
				options.format = SaveDocumentType.JPEG;
				options.optimized = true;
			}


			// Do export
			exportFile = new File(parentPath + '/' + app.activeDocument.name.slice(0, -4) + '_' + attributeName+selection2);
			activeDocument.exportDocument(exportFile, ExportType.SAVEFORWEB, options);


			// Make tx file
      // Maya seems to overwrite the generated tx file no matter what so generating it at export time makes no sense.

			// command = '"' + MAKETX_PATH + '" -v -u --unpremult --oiio "' + exportFile.fsName + '"';
			// var commandFile = new File(Folder.desktop + '/tempAutoConnectExporter.bat')
			// commandFile.open ('w')
			// commandFile.write(command)
			// commandFile.close()
			// cmd = app.system('cmd /c "' + commandFile.fsName + '"');
		} catch(e){
			self.window.close();
		};
		self.window.close();
	}
	this.show = function(){
		self.window.show();
	};
}
