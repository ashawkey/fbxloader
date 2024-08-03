# a minimal scene graph implementation based on threejs
import numpy as np


class Object3D:
    def __init__(self, id):
        self.id = id # id of the object, should be unique!
        self.parent = None
        self.children = []
        self.matrix = np.eye(4) # local transformation matrix
        self.matrixWorld = np.eye(4) # world (global) transformation matrix, accumulated from parent matrices
    
    def get(self, id):
        if self.id == id:
            return self
        for child in self.children:
            obj = child.get(id)
            if obj is not None:
                return obj
        return None
    
    def add(self, obj):
        obj.removFromParent()
        obj.parent = self
        self.children.append(obj)
    
    def remove(self, obj):
        if obj in self.children:
            self.children.remove(obj)
            obj.parent = None
    
    def removFromParent(self):
        if self.parent is not None:
            self.parent.remove(self)
    
    # call this after building the graph!
    def updateMatrixWorld(self):
        if self.parent is not None:
            self.matrixWorld = np.dot(self.parent.matrixWorld, self.matrix)
        else:
            self.matrixWorld = self.matrix
        for child in self.children:
            child.updateMatrixWorld()

    def applyMatrix(self, matrix):
        # update local matrix
        self.matrix = np.dot(matrix, self.matrix)
        # update world matrix
        self.updateMatrixWorld()
    
    def traverse(self, callback):
        callback(self)
        for child in self.children:
            child.traverse(callback)


class Mesh(Object3D):
    def __init__(self, id, vertices=None, faces=None):
        super().__init__(id)
        # we will not use the geometry abstraction...
        self.vertices = vertices
        self.faces = faces
        self.material = None # not implemented


class Scene(Object3D):
    def __init__(self, id):
        super().__init__(id)
        # currently nothing is implemented here
        