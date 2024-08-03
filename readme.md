## FBXLoader for Python

> [!WARNING]
> This library has very limited features and is only intended for **reading mesh geometry from binary FBX files**, it doesn't support:
> * Reading ASCII FBX files.
> * Reading textures and materials even if they are encoded in the file.
> * Reading skeletons and animations. Note that the geometry may also be incorrect if the mesh is skinned.
> * Writing FBX files.

However, this can be a starting point to implement more features in the future. Welcome to contribute!


### Install

```bash
# from pypi
pip install fbxloader

# from source
pip install git+https://github.com/ashawkey/fbxloader.git
```

### Usage

Python API:
```python
from fbxloader import FBXLoader

fbx = FBXLoader('model.fbx') # load from file or bytes

# similar to glb, fbx usually contains multiple meshes as a scene
# we provide a method to merge them into a single mesh and export as trimesh.Trimesh
mesh = fbx.export_trimesh()

# write to other formats (using trimesh API)
mesh.export('model.obj')

# meta: this is to provide some information on unimplemented features, you may inspect it to make sure if the model is expected to load correctly. e.g., hasDeformers=True usually means the model is skinned.
print(fbx.meta)
# {'hasImages': False, 'hasTextures': False, 'hasMaterials': True, 'hasDeformers': True, 'hasAnimations': True}
```

We also provide a CLI tool:
```bash
fbxconverter <input.fbx> <output.obj/ply/glb>
```

Lastly, we provide a testing script and also a fbx mesh as an example:
```bash
python tests/test.py examples/annulus.fbx
```

### Reference
The code is basically translated from [threejs's FBXLoader](https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js). 
Thanks to the threejs team and also copilot!