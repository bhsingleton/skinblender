# Ez Skin Blender
A DCC-agnostic selection-based skin weighting tool.  
  
## Installation
This tool is reliant on the following python packages: six, Qt.py, scipy, numpy and dcc.  
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

## PIP Dependencies
To install the required pip dependencies open a Command Prompt window.  
I will be using Maya 2022 for this example. Be sure to adjust your code for whatever version of Maya you are using. 
Change the current working directory using:  
> cd %PROGRAMFILES%\Autodesk\Maya2022\bin  

Make sure you have pip installed using:  
> mayapy.exe -m ensurepip --upgrade --user  

Now you can install the necessary dependencies using:  
> mayapy.exe -m pip install six --user  

Be sure to repeat this for: six, Qt.py and scipy.  
At this point in time dcc is currently not available through pip.
