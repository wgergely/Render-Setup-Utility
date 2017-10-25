## Synopsis

**Render Setup Utility** is a Maya tool I wrote to help manage my workflow, and predominantly to help setting render scenes up. It provides shortcuts to ease the management and adding of Arnold property overrides and collection assignments as well as other various convenience functions.

## Why & How

I often use shader assignments as the basis to organise my scenes.
For instance, in the case of, say, a _'house'_ I would use the following shader naming convention:

> _house1_roof_
> _house1_doorFrame_
> _house1_doorHandle_
> _house1_chimney_
> ... etc.

**'house1'** becomes the main group, and **'roof'** is a sub-item of that group. Each shader in effect describes a **set** via the shader assignments.

As only renderable objects can have shader assignments, I find this an ideal and quick way to organise render scenes.

You can toggle these groups easily via the utility window:

>![Off](https://lh3.googleusercontent.com/39v_N8IaQM6N01jlX8lnHJ96Nbr2OdTg61Xez8Ck97bLiurIJULPsRLTi3f5l3LEo8qLIfPlLjY86Ww=w1443-h920)
>![On](https://lh3.googleusercontent.com/5QJRFys5EIeWigb_ZL1h-RuVhutLAQj221o5V1WfgMo_UeF-4YFIKDwxWK6SWElxLZXJfnuzWRruk-g=w1443-h920)

It is also easy to batch add and edit arnold property overrides or shader overrides:
>![enter image description here](https://lh3.googleusercontent.com/0NPkp-3geS4bBvOWOKamW2I4nzYI0XtFiHFINAXF0Xo00-8aCXmk1b4XJLE1wxufvuWRNb57jMuqMSc=w1443-h920)

Tool to create and assign shaders:
> ![enter image description here](https://lh3.googleusercontent.com/KeFnwElak2S2gSwFUIYNAgCDmzxaTmWYPdWZdJhGqp62BTfbcHkM1QoLaU68CyTvT61YUUYrAQghDFw=w1443-h920)

----------
## Installation

Get the repository from GitHub and place it into the folder where your Maya.env PYTHONPATH is pointing to. Alternatively, you can append the location via the script editor by running:

```
import sys
sys.path.append( '/location/to/RenderSetupUtility' )
```

To open the tool run the following in the script-editor:

```
import RenderSetupUtility.main.ui as rsuUI
rsuUI.createUI()
```

## Notes

This is a work-in-progress utility and is there are plenty of bugs I'm sure so please take care. I haven't tested it outside my own little work environment so who knows, it might be broken.
