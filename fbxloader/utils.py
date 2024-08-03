import numpy as np
from scipy.spatial.transform import Rotation as R

EULER_ORDERS = ['ZYX', 'YZX', 'XZY', 'ZXY', 'YXZ', 'XYZ']

def get_transform(transformData: dict):
    # ref: https://github.com/mrdoob/three.js/blob/b1046960d9adb597ba0ead7ff4a31f16d0a49a79/examples/jsm/loaders/FBXLoader.js#L4116
    # don't understand the code at all, but it should be the same as the reference...

    inheritType = transformData.get('inheritType', 0)
    eulerOrder = transformData.get('eulerOrder', 'ZYX').lower()

    lTranslationM = np.eye(4)
    lPreRotationM = np.eye(4)
    lRotationM = np.eye(4)
    lPostRotationM = np.eye(4)
    lScalingM = np.eye(4)
    lScalingPivotM = np.eye(4)
    lScalingOffsetM = np.eye(4)
    lRotationOffsetM = np.eye(4)
    lRotationPivotM = np.eye(4)
    lParentGX = np.eye(4)
    lParentLX = np.eye(4)
    lGlobalT = np.eye(4)

    if 'translation' in transformData: # float array of 3
        lTranslationM[:3, 3] = np.array(transformData['translation'])
    if 'preRotation' in transformData: # degrees in euler order, float array of 3
        lPreRotationM[:3, :3] = R.from_euler(eulerOrder, transformData['preRotation'], degrees=True).as_matrix()
    if 'rotation' in transformData:
        lRotationM[:3, :3] = R.from_euler(eulerOrder, transformData['rotation'], degrees=True).as_matrix()
    if 'postRotation' in transformData:
        lPostRotationM[:3, :3] = R.from_euler(eulerOrder, transformData['postRotation'], degrees=True).as_matrix()
        lPostRotationM = np.linalg.inv(lPostRotationM)

    if 'scale' in transformData: # float array of 3
        lScalingM[:3, :3] = np.diag(transformData['scale'])

    if 'scalingOffset' in transformData: # float array of 3
        lScalingOffsetM[:3, 3] = np.array(transformData['scalingOffset'])
    if 'scalingPivot' in transformData: # float array of 3
        lScalingPivotM[:3, 3] = np.array(transformData['scalingPivot'])
    if 'rotationOffset' in transformData: # float array of 3
        lRotationOffsetM[:3, 3] = np.array(transformData['rotationOffset'])
    if 'rotationPivot' in transformData: # float array of 3
        lRotationPivotM[:3, 3] = np.array(transformData['rotationPivot'])
    
    if 'parentMatrixWorld' in transformData:
        lParentLX = np.array(transformData['parentMatrix'])
        lParentGX = np.array(transformData['parentMatrixWorld'])
    
    lLRM = lPreRotationM @ lRotationM @ lPostRotationM

    lParentGRM = np.eye(4)
    lParentGRM[:3, :3] = lParentGX[:3, :3] / np.linalg.norm(lParentGX[:3, :3], axis=1, keepdims=True)
    lParentTM = np.eye(4)
    lParentTM[:3, 3] = lParentGX[:3, 3]

    lParentGRSM = np.linalg.inv(lParentTM) @ lParentGX
    lParentGSM = np.linalg.inv(lParentGRM) @ lParentGRSM

    if inheritType == 0:
        lGlobalRS = lParentGRM @ lLRM @ lParentGSM @ lScalingM
    elif inheritType == 1:
        lGlobalRS = lParentGRM @ lParentGSM @ lLRM @ lScalingM
    else:
        lParentLSM = np.eye(4)
        lParentLSM[:3, :3] = np.diag(np.linalg.norm(lParentLX[:3, :3], axis=0))
        lParentLSM_inv = np.linalg.inv(lParentLSM)
        lParentGSM_noLocal = lParentGSM @ lParentLSM_inv
        lGlobalRS = lParentGRM @ lLRM @ lParentGSM_noLocal @ lScalingM

    lRotationPivotM_inv = np.linalg.inv(lRotationPivotM)
    lScalingPivotM_inv = np.linalg.inv(lScalingPivotM)

    lTransform = lTranslationM @ lRotationOffsetM @ lRotationPivotM @ lPreRotationM @ lRotationM @ lPostRotationM @ lRotationPivotM_inv @ lScalingOffsetM @ lScalingPivotM @ lScalingM @ lScalingPivotM_inv

    lLocalTWithAllPivotAndOffsetInfo = np.eye(4)
    lLocalTWithAllPivotAndOffsetInfo[:3, 3] = lTransform[:3, 3]

    lGlobalTranslation = lParentGX @ lLocalTWithAllPivotAndOffsetInfo
    lGlobalT[:3, 3] = lGlobalTranslation[:3, 3]

    lTransform = lGlobalT @ lGlobalRS
    lTransform = np.linalg.inv(lParentGX) @ lTransform

    return lTransform