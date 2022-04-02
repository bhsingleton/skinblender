# Ez Skin Blender
A DCC-agnostic selection-based skin weighting tool.  
  
## Installation
This tool is reliant on the following python packages: six, scipy, numpy and dcc.  
Once you've acquired these packages you can launch the tool with the following command:  
  
> from ezskinblender import qezskinblender;  
> window = qezskinblender.QEzSkinBlender();  
> window.show();  
  
## Hotkeys
Creating hotkeys is super easy.  
QVertexBlender is derived from QProxyWindow which uses a singleton pattern for instances.  
An example of a hotkey can be as simple as:  
  
> from ezskinblender import qezskinblender;  
> window = qezskinblender.QEzSkinBlender.getInstance();  
> window.blendVertices();  
  
## Maya Interface
To utilize vertex colour feedback users will need to download and install the following plugin:  
https://github.com/bhsingleton/TransferPaintWeightsCmd  
![image](https://user-images.githubusercontent.com/11181168/132901302-797e56fe-656c-489b-ba55-0f70898cd6b8.png)
  
## 3ds Max Interface
![image](https://user-images.githubusercontent.com/11181168/132901382-f94ce17a-9c9a-434b-a1c6-d1db5a39acc4.png)
