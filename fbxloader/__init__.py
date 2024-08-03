import zlib
import struct
import trimesh
import numpy as np
from numbers import Number
from typing import Optional, Union

from .utils import get_transform, EULER_ORDERS
from .nodes import Scene, Mesh, Object3D

class BinaryReader:
    def __init__(self, data):
        self.data = data
        self.index = 0
    
    def __len__(self):
        return len(self.data)
    
    def skip(self, size):
        self.index += size

    def bytes(self, size):
        b = self.data[self.index:self.index+size]
        self.index += size
        return b
    
    def string(self, size):
        # s = bytes(struct.unpack('<' + 'B' * size, self.data[self.index:self.index+size])).decode() # little-endian, n unsigned chars (B, 1 byte)
        return self.bytes(size).decode()
    
    def uint8(self):
        i = struct.unpack('<B', self.data[self.index:self.index+1])[0]
        self.index += 1
        return i

    def uint32(self):
        i = struct.unpack('<I', self.data[self.index:self.index+4])[0] # little-endian, 1 unsigned int (I, 4 bytes)
        self.index += 4
        return i

    def uint64(self):
        i = struct.unpack('<Q', self.data[self.index:self.index+8])[0]
        self.index += 8
        return i

    def bool(self):
        # ref: https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js#L3789
        return (self.uint8() & 1) == 1

    def bool_array(self, size):
        return [self.bool() for i in range(size)]

    def int16(self):
        i = struct.unpack('<h', self.data[self.index:self.index+2])[0] # little-endian, 1 signed short (h, 2 bytes)
        self.index += 2
        return i

    def int32(self):
        i = struct.unpack('<i', self.data[self.index:self.index+4])[0] # little-endian, 1 signed int (i, 4 bytes)
        self.index += 4
        return i

    def int32_array(self, size):
        return [self.int32() for i in range(size)]

    def int64(self):
        i = struct.unpack('<q', self.data[self.index:self.index+8])[0] # little-endian, 1 signed long long (q, 8 bytes)
        self.index += 8
        return i

    def int64_array(self, size):
        return [self.int64() for i in range(size)]

    def float32(self):
        f = struct.unpack('<f', self.data[self.index:self.index+4])[0] # little-endian, 1 float (f, 4 bytes)
        self.index += 4
        return f
    
    def float32_array(self, size):
        return [self.float32() for i in range(size)]
    
    def float64(self):
        f = struct.unpack('<d', self.data[self.index:self.index+8])[0] # little-endian, 1 double (d, 8 bytes)
        self.index += 8
        return f

    def float64_array(self, size):
        return [self.float64() for i in range(size)]
    

def parse_binary_fbx(data):
    # data: bytes for fbx file
    # return: dict of fbx tree

    reader = BinaryReader(data)
    
    # data[0:21] is the header
    header = reader.string(21)
    assert header == 'Kaydara FBX Binary  \x00', f'Invalid binary FBX header: {header}'

    # data[21:23] is (0x1A, 0x00), but seems to be unknown
    reader.skip(2)

    # data[23:27] is the version (e.g. 7400 for 7.4)
    version = reader.uint32()
    assert version >= 6400, f'Unsupported FBX version {version}, must be greater than 6400'

    # footer is 160 bytes magic + 16 bytes padding
    def end_of_content():
        # ref: https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js#L3477
        if len(reader) % 16 == 0:
            return ((reader.index + 160 + 16) & ~0xf) >= len(reader)
        else:
            return (reader.index + 160 + 16) >= len(reader)

    # recursively parse the rest of the data
    def parse_property():

        propertyType = reader.string(1)

        if propertyType == 'C': return reader.bool()
        elif propertyType == 'D': return reader.float64()
        elif propertyType == 'F': return reader.float32()
        elif propertyType == 'I': return reader.int32()
        elif propertyType == 'L': return reader.int64()
        elif propertyType == 'R': return reader.bytes(reader.uint32())
        elif propertyType == 'S': return reader.string(reader.uint32())
        elif propertyType == 'Y': return reader.int16()
        elif propertyType in ['b', 'c', 'd', 'f', 'i', 'l']:
            length = reader.uint32()
            encoding = reader.uint32() # 0 = raw, 1 = zipped
            compressedLength = reader.uint32()
            if encoding == 0:
                if propertyType == 'b': return reader.bool_array(length)
                elif propertyType == 'c': return reader.bool_array(length) # same as 'b'
                elif propertyType == 'd': return reader.float64_array(length)
                elif propertyType == 'f': return reader.float32_array(length)
                elif propertyType == 'i': return reader.int32_array(length)
                elif propertyType == 'l': return reader.int64_array(length)
            else:
                buffer = reader.bytes(compressedLength)
                data2 = zlib.decompress(buffer)
                reader2 = BinaryReader(data2)
                if propertyType == 'b': return reader2.bool_array(length)
                elif propertyType == 'c': return reader2.bool_array(length) # same as 'b'
                elif propertyType == 'd': return reader2.float64_array(length)
                elif propertyType == 'f': return reader2.float32_array(length)
                elif propertyType == 'i': return reader2.int32_array(length)
                elif propertyType == 'l': return reader2.int64_array(length)
        else:
            raise Exception(f'Unknown property type {propertyType}')

    def parse_subNode(name, node, subNode):
        # ref: https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js#L3540
        # I don't understand a line of the following mess, but it should follow the reference...
        if subNode['singleProperty']:
            value = subNode['propertyList'][0]
            if isinstance(value, list):
                node[subNode['name']] = subNode
                subNode['a'] = value
            else:
                node[subNode['name']] = value
        elif name == 'Connections' and subNode['name'] == 'C':
            array = []
            for i in range(1, len(subNode['propertyList'])): # skip the first element
                array.append(subNode['propertyList'][i])
            if 'connections' not in node:
                node['connections'] = []
            node['connections'].append(array)
        elif subNode['name'] == 'Properties70':
            for k, v in subNode.items():
                node[k] = v
        elif name == 'Properties70' and subNode['name'] == 'P':
            innerPropName = subNode['propertyList'][0]
            innerPropType1 = subNode['propertyList'][1]
            innerPropType2 = subNode['propertyList'][2]
            innerPropFlag = subNode['propertyList'][3]

            if innerPropName.startswith('Lcl'): innerPropName = innerPropName.replace('Lcl ', 'Lcl_')
            if innerPropType1.startswith('Lcl'): innerPropType1 = innerPropType1.replace('Lcl ', 'Lcl_')

            if innerPropType1 in ['Color', 'ColorRGB', 'Vector', 'Vector3D'] or innerPropType1.startswith('Lcl_'):
                innerPropValue = [
                    subNode['propertyList'][4],
                    subNode['propertyList'][5],
                    subNode['propertyList'][6]
                ]
            else:
                # maybe undefined...
                if len(subNode['propertyList']) > 4:
                    innerPropValue = subNode['propertyList'][4]
                else:
                    innerPropValue = None

            node[innerPropName] = {
                'type': innerPropType1,
                'type2': innerPropType2,
                'flag': innerPropFlag,
                'value': innerPropValue
            }

        elif subNode['name'] not in node:
            if 'id' in subNode:
                node[subNode['name']] = {subNode['id']: subNode}
            else:
                node[subNode['name']] = subNode
        else:
            if subNode['name'] == 'PoseNode':
                if not isinstance(node[subNode['name']], list):
                    node[subNode['name']] = [node[subNode['name']]]
                node[subNode['name']].append(subNode)
            elif 'id' in subNode and subNode['id'] not in node[subNode['name']]:
                node[subNode['name']][subNode['id']] = subNode


    def parse_node():
        node = {}
        
        # 3 version-dependent size
        endOffset = reader.uint64() if version >= 7500 else reader.uint32()
        numProperties = reader.uint64() if version >= 7500 else reader.uint32()
        propertyListLen = reader.uint64() if version >= 7500 else reader.uint32()

        nameLen = reader.uint8()
        name = reader.string(nameLen)

        if endOffset == 0:
            return None

        propertyList = []
        for i in range(numProperties):
            propertyList.append(parse_property())
        
        while endOffset > reader.index:
            subNode = parse_node()
            if subNode is not None:
                parse_subNode(name, node, subNode)
        
        if name != '': node['name'] = name
        if len(propertyList) > 0 and isinstance(propertyList[0], Number): node['id'] = propertyList[0]
        if len(propertyList) > 1: node['attrName'] = propertyList[1]
        if len(propertyList) > 2: node['attrType'] = propertyList[2]
        node['singleProperty'] = numProperties == 1 and reader.index == endOffset
        node['propertyList'] = propertyList

        return node

    fbxtree = {}
    while not end_of_content():
        node = parse_node()
        if node is not None:
            fbxtree[node['name']] = node
        
    return fbxtree


class FBXLoader:
    def __init__(self, path_or_blob: Optional[Union[str, bytes]]):

        ### parse binary fbx into tree
        if isinstance(path_or_blob, str):
            with open(path_or_blob, "rb") as f:
                data = f.read()
        else:
            data = path_or_blob

        self.fbxtree = parse_binary_fbx(data)

        ### data holders
        self.connections = {} # nodeID -> {parents: [{ID, relationship}], children: [{ID, relationship}]}
        self.objects = {} # nodeID -> Object3D

        self.scene = Scene(id=0) # root object (FBX always use 0 as root)
        self.objects[0] = self.scene

        # meta for some unimplemented features which may lead to wrong geometry
        self.meta = { 
            'hasImages': False,
            'hasTextures': False,
            'hasMaterials': False,
            'hasDeformers': False,
            'hasAnimations': False,
        }

        ### parse connections
        if 'Connections' in self.fbxtree: 
            raw_connections = self.fbxtree['Connections']['connections']
            for connection in raw_connections:
                fromId = connection[0] # child
                toId = connection[1] # parent
                relationship = connection[2] if len(connection) > 2 else None
                # build bidirectional graph
                if fromId not in self.connections:
                    self.connections[fromId] = {
                        'parents': [],
                        'children': []
                    }
                self.connections[fromId]['parents'].append({'ID': toId, 'relationship': relationship})
                if toId not in self.connections:
                    self.connections[toId] = {
                        'parents': [],
                        'children': []
                    }
                self.connections[toId]['children'].append({'ID': fromId, 'relationship': relationship})
        
        ### unimplemented things
        # ref: https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js#L163
        # Images
        if 'Video' in self.fbxtree['Objects']:
            self.meta['hasImages'] = True

        # Textures
        if 'Texture' in self.fbxtree['Objects']:
            self.meta['hasTextures'] = True

        # Materials
        if 'Material' in self.fbxtree['Objects']:
            self.meta['hasMaterials'] = True

        # Deformers (some geometry seems to depend on this... but currently just ignored...)
        if 'Deformer' in self.fbxtree['Objects']:
            self.meta['hasDeformers'] = True

        # Animations
        if 'AnimationCurve' in self.fbxtree['Objects']:
            self.meta['hasAnimations'] = True

        ### parse Geometry (partially implemented...)

        if 'Geometry' in self.fbxtree['Objects']:
                
            for nodeID, node in self.fbxtree['Objects']['Geometry'].items():
                
                relationships = self.connections[int(nodeID)]

                # find parent model node
                modelNodes = [self.fbxtree['Objects']['Model'][parent['ID']] for parent in relationships['parents']]

                if len(modelNodes) == 0:
                    continue

                modelNode = modelNodes[0] # take the first as the parent model node

                # build pre-transformation matrix from parent model node
                preTransformData = {}
                if 'RotationOrder' in modelNode:
                    preTransformData['eulerOrder'] = EULER_ORDERS[modelNode['RotationOrder']['value']]
                if 'InheritType' in modelNode:
                    preTransformData['inheritType'] = int(modelNode['InheritType']['value'])
                if 'GeometricTranslation' in modelNode:
                    preTransformData['translation'] = modelNode['GeometricTranslation']['value']
                if 'GeometricRotation' in modelNode:
                    preTransformData['rotation'] = modelNode['GeometricRotation']['value']
                if 'GeometricScaling' in modelNode:
                    preTransformData['scale'] = modelNode['GeometricScaling']['value']
                    
                preTransform = get_transform(preTransformData)

                # build geometry
                if 'Vertices' not in node or 'PolygonVertexIndex' not in node:
                    continue

                vertexPositions = node['Vertices']['a'] # list of floats
                vertexIndices = node['PolygonVertexIndex']['a'] # list of ints, negative means end of polygon

                vertices = np.array(vertexPositions).reshape(-1, 3)

                # apply preTransform
                vertices = np.hstack([vertices, np.ones((vertices.shape[0], 1))]).T
                vertices = preTransform @ vertices
                vertices = vertices[:3].T

                faces = []

                cur_face = []
                for i, vertexIndex in enumerate(vertexIndices): # have to loop... maybe slow
                    # negative vertexIndex denote end of a polygon
                    if vertexIndex < 0:
                        vertexIndex = -vertexIndex - 1
                        cur_face.append(vertexIndex)
                        # triangulate (NOTE: assume polygon vertices are ordered)
                        v0 = cur_face[0]
                        for j in range(len(cur_face) - 2):
                            v1 = cur_face[j+1]
                            v2 = cur_face[j+2]
                            faces.append([v0, v1, v2])
                        cur_face = []
                    else:
                        cur_face.append(vertexIndex)
                
                faces = np.array(faces)

                mesh = Mesh(nodeID, vertices, faces)

                self.objects[nodeID] = mesh

        ### parse Models
        # model nodes are usually parents to geometry, which contains local transformation 
        for nodeID, node in self.fbxtree['Objects']['Model'].items():
            
            transformData = {}
            if 'RotationOrder' in node:
                transformData['eulerOrder'] = EULER_ORDERS[node['RotationOrder']['value']]
            if 'InheritType' in node:
                transformData['inheritType'] = int(node['InheritType']['value'])
            if 'Lcl_Translation' in node:
                transformData['translation'] = node['Lcl_Translation']['value']
            if 'PreRotation' in node:
                transformData['preRotation'] = node['PreRotation']['value']
            if 'Lcl_Rotation' in node:
                transformData['rotation'] = node['Lcl_Rotation']['value']
            if 'PostRotation' in node:
                transformData['postRotation'] = node['PostRotation']['value']
            if 'Lcl_Scaling' in node:
                transformData['scale'] = node['Lcl_Scaling']['value']
            if 'ScalingOffset' in node:
                transformData['scalingOffset'] = node['ScalingOffset']['value']
            if 'ScalingPivot' in node:
                transformData['scalingPivot'] = node['ScalingPivot']['value']
            if 'RotationOffset' in node:
                transformData['rotationOffset'] = node['RotationOffset']['value']
            if 'RotationPivot' in node:
                transformData['rotationPivot'] = node['RotationPivot']['value']
            
            transform = get_transform(transformData)

            obj = Object3D(nodeID)
            obj.matrix = transform

            self.objects[nodeID] = obj
        
        ### build scene recursively from graph (connections)

        def build_scene(nodeID):
            if nodeID not in self.objects:
                return None

            obj = self.objects[nodeID]
            for x in self.connections[nodeID]['children']:
                child = build_scene(x['ID'])
                if child is not None:
                    obj.add(child)
            
            return obj

        build_scene(0)
        self.scene.updateMatrixWorld() # update world matrices using parent-child relationships and local matrices

    
    def export_trimesh(self):
        # export Scene to a signle trimesh.Trimesh

        submeshes = []

        def extract(node):
            if isinstance(node, Mesh):
                # apply transformation
                vertices = np.hstack([node.vertices, np.ones((node.vertices.shape[0], 1))]).T
                vertices = node.matrixWorld @ vertices
                vertices = vertices[:3].T
                # create Trimesh
                submesh = trimesh.Trimesh(vertices=vertices, faces=node.faces)
                submeshes.append(submesh)
        
        self.scene.traverse(extract)
        mesh = trimesh.util.concatenate(submeshes)

        return mesh

