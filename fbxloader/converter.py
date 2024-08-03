import trimesh
from . import FBXLoader

def main():
    import argparse
    parser = argparse.ArgumentParser(description='FBX Converter')
    parser.add_argument('file', type=str, help='FBX file to load')
    parser.add_argument('output', type=str, default='out.ply', help='Output file')
    args = parser.parse_args()

    fbx = FBXLoader(args.file)
    mesh = fbx.export_trimesh()
    mesh.export(args.output)

if __name__ == "__main__":
    main()