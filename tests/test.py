import sys
sys.path.append('.')

import argparse
from pprint import pprint
from fbxloader import FBXLoader

parser = argparse.ArgumentParser(description='FBX Loader')
parser.add_argument('file', type=str, help='FBX file to load')
parser.add_argument('--output', type=str, default='out.ply', help='Output file')
args = parser.parse_args()

fbx = FBXLoader(args.file)

print(fbx.meta)

mesh = fbx.export_trimesh()

# normalize mesh vertices (FBX tends to have extremely large range...)
vmin, vmax = mesh.vertices.min(axis=0), mesh.vertices.max(axis=0)
center = (vmin + vmax) / 2
scale = 2 / (vmax - vmin).max()
mesh.vertices = (mesh.vertices - center) * scale

# write to another format for verification
mesh.export(args.output)

# write the ASCII FBX tree to a file for deubgging
with open(args.output + '.txt', 'w') as f:
    pprint(fbx.fbxtree, f)
