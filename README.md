# vptools
Here is a toolset for Maya that provides a way of creating and editing widgets in a viewport. 
Widgets can execute python code or select nodes in Maya.

![Logo](/test.gif)

Now it's in a development stage, ready for testing and improving!

**Usage**
1. Clone or download repository to some folder (*c:/vptools*)
2. Open vptools.py, change VPToolsDirectory to your path (*c:/vptools*)
3. Run vptools.py in Maya via `execfile("c:/vptools/vptools.py")`

Press tab to browse available widgets.
`$NAMESPACE` can be used in widget's scripts. It's substituted with a currently selected node's namespace.

Widgets are saved as xml in *maya/project/vptools* or *vptools/controls*

Overlays are used to make widgets visible in a viewport. It's just a Qt graphics view widget with a transparency set. No magic.
Callbacks are installed to show and hide widgets when it's necessary.
