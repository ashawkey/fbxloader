## FBXLoader for Python

[!WARNING]
This library has very limited features and is only intended for **reading mesh geometry from binary FBX files**, it doesn't support:
* Reading ASCII FBX files.
* Reading textures and materials even if they are encoded in the file.
* Reading skeletons and animations. Note that the geometry may also be incorrect if the mesh is skinned.
* Writing FBX files.

However, this can be a starting point to implement more features in the future. Welcome to contribute!


### Install

```bash
# from pypi
pip install fbxloader

# from source
pip install git+https://github.com/ashawkey/fbxloader.git
```

### Usage

```python
from fbxloader import FBXLoader

fbx = FBXLoader('model.fbx') # load from file or bytes

# similar to glb, fbx usually contains multiple meshes as a scene
# we provide a method to merge them into a single mesh and export as trimesh.Trimesh
mesh = fbx.export_trimesh()

# write to other formats (using trimesh API)
mesh.export('model.obj')
```

We provide a testing script and also a fbx mesh example:
```bash
python tests/test.py examples/annulus.fbx
```