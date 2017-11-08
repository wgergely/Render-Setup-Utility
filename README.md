## Render Setup Utility

Render Setup Utility is a Maya utility that let's you quickly add objects to render-layer collections. The collections are based on shader names and their assignments.

## Shader-Assignments as Selection Sets

Most of the time only renderable objects have shader assignments, hence I find this a quick way to organise renderable elements independent of other scene objects.

For instance, in the case of a **house** asset, I would group my renderable elements via their shader assignments.

The way I do this is simply to be strict when naming my shaders.
I use the following name-pattern:

>*house_roof1*  
>*house_doorFrame1*  
>*house_doorHandle1*  
>*house_chimney1*  
> _... etc._

**house** is the main *group*, while **roof1, doorFrame1, doorHandle1** and **chimney1** are sub-items of the **house** group.

Each shader in effect describes a **selection set** via their assignments.


## Usage

Any shaders assigned to a mesh will be recognized and listed by the utility.  
When inactive, you will see the shader's name, type, and the number of objects assigned to it:

![Screenshot](/images/renderSetupUtility_overview1.png?raw=true)

We can then add these shaders to the active render layer. The active render layer does not have to be  visible. In fact, working on the visible render layer can be slow at times, especially when adding, removing hundreds of objects.

![Screenshot](/images/renderSetupUtility_overview2.png?raw=true)

If when adding the items any of the override boxes are ticked, the collections will contain the appropiate render property overrides for Arnold, and/or a shader (not material) override.

![Screenshot](/images/renderSetupUtility_overview3.png?raw=true "Arnold Propery Overrides")

Namespaces can be useful to further partition the scene. Note that mattes will be indicated via the ui.

![Screenshot](/images/renderSetupUtility_overview5.png?raw=true)

You can create shaders with the appropriate naming convention with the shader group button. The created shader will automatically be assigned to any selected meshes.

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

...
