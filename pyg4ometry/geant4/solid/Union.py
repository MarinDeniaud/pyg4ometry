from SolidBase import SolidBase as _SolidBase
from ..Registry import registry as _registry
from ...exceptions import *
from ...transformation import *

import copy as _copy

class Union(_SolidBase):
    """
    name = name
    obj1 = unrotated, untranslated solid
    obj2 = solid rotated and translated according to tra2
    tra2 = [rot,tra] = [[a,b,g],[dx,dy,dz]]
    """
    def __init__(self, name, obj1, obj2, tra2):
        self.type = "Union"
        self.name = name
        self.obj1 = obj1
        self.obj2 = obj2
        self.tra2 = tra2
        self.mesh = None 
        _registry.addSolid(self)

    def __repr__(self):
        return 'Union : ('+str(self.obj1)+') with ('+str(self.obj2)+')'

    def pycsgmesh(self):

        #print 'Union ',self.name, self.obj1.name, self.obj2.name

#        if self.mesh :
#            return self.mesh
        
        rot = tbxyz(self.tra2[0])
        tlate = self.tra2[1]

        m1 = self.obj1.pycsgmesh()
        m2 = _copy.deepcopy(self.obj2.pycsgmesh()) # need top copy this mesh as it is transformed
        m2.rotate(rot[0],-rad2deg(rot[1]))
        m2.translate(tlate)
        self.obj2mesh = m2

        self.mesh = m1.union(m2)
        if not self.mesh.toPolygons():
            print 'Union null mesh',self.name,self.obj1.name, m1, self.obj2.name, m2
            raise NullMeshError(self.obj1, self.obj2, "Union")

        self.obj1.mesh = None
        self.obj2.mesh = None

        #print 'union mesh ', self.name
        return self.mesh

   