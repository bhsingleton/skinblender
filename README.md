# Skin Blender
A DCC-agnostic vertex selection based skin weighting tool.  

## Installing the PIP Dependencies
To install the required pip dependencies open a Command Prompt window.  
In this example I will be using Maya 2025. Be sure to adjust your code to whichever version of Maya you are using.  
Change the current working directory using:  
> cd %PROGRAMFILES%\Autodesk\Maya2025\bin  

Make sure you have pip installed using:  
> mayapy.exe -m ensurepip --upgrade --user  

Now you can install the necessary dependencies using:  
> mayapy.exe -m pip install scipy --user  

## Usage
Once you've downloaded `skinblender`, move the folder into one of the Maya script directories.  
You will also need to repeat this process for the `dcc` package: https://github.com/bhsingleton/dcc/  
Once you're done you can launch the tool with the following command:  
  
> from skinblender.ui import qskinblender;  
> window = qskinblender.QSkinBlender();  
> window.show();  
  
## Hotkeys
Creating hotkeys is super easy.  
The main window `QSkinBlender` is derived from `QProxyWindow` which uses a singleton pattern for instancing.  
So an example of a hotkey can be as simple as:  
  
> from skinblender.ui import qskinblender;  
> window = qskinblender.QSkinBlender.getInstance();  
> window.blendVertices();  
  
## Maya Interface
To utilize vertex colour feedback users will need to download and install the following plugin:  
https://github.com/bhsingleton/TransferPaintWeightsCmd  
![image](https://user-images.githubusercontent.com/11181168/132901302-797e56fe-656c-489b-ba55-0f70898cd6b8.png)
  
## 3ds Max Interface
![image](https://user-images.githubusercontent.com/11181168/132901382-f94ce17a-9c9a-434b-a1c6-d1db5a39acc4.png)
