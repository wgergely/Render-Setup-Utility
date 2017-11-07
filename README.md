## Synopsis

**Render Setup Utility** is a Maya utility intended ease setting render scenes up. It provides shortcuts to management adding collections with  pre-defined overrides based on in-scene shader-assignments.

## Shader-Assignments as Selection Sets

I like to use shader-assignments as the basis to organise my render scenes.
For instance, in the case of a **house** asset, I would group my renderable elements via their shader assignments.

The way I do this is simply to be strict when naming my shaders.
I use the following naming convention:

>*house_roof1*  
>*house_doorFrame1*  
>*house_doorHandle1*  
>*house_chimney1*  
> _... etc._

**house** is the main *group*, while **roof1, doorFrame1, doorHandle1** and **chimney1** are sub-items of the **house** group. Each shader in effect describes a **selection set** via the shader assignments.

Most of the time only renderable objects have shader assignments, so I find this an ideal and quick way to organise render scenes independent of other scene elements.

## Usage

This tool gives you shortcuts to quickly add these groups to the current render layer as collections.

*The below shaders are present and assigned to a mesh in the scene. Unassigned shaders are ignored automatically:*  
![Screenshot](/images/renderSetupUtility_overview1.png?raw=true)

*After adding the shaders to the 'house1_rsLayer' render setup layer:*  
![Screenshot](/images/renderSetupUtility_overview2.png?raw=true)

*It is also easy to batch add and edit Arnold property overrides and shader overrides. When overriding with a shader override displacements connected to the shading group will not be overriden. (this would require a material override, but I didn't implement this)*  
![Screenshot](/images/renderSetupUtility_overview3.png?raw=true "Arnold Propery Overrides")

*Namespaces can be useful to further partition the scene.*  
![Screenshot](/images/renderSetupUtility_overview5.png?raw=true)

*There's also a little window to create shaders with the appropriate naming convention. The created shader will automatically be assigned to any selected meshes.*  
![Screenshot](/images/renderSetupUtility_overview4.png?raw=true)

## Installation

Get the repository from GitHub and place it into the folder where your Maya.env PYTHONPATH is pointing to. Alternatively, you can append the location via the script editor by running:

```
import sys
sys.path.append( '/path/to/modules' )
```

To launch the window:

```
import RenderSetupUtility
RenderSetupUtility.show()
```

## Notes

This is a work-in-progress module and is there are plenty of bugs. I haven't tested it outside my own little work environment so who knows, it might be broken.
