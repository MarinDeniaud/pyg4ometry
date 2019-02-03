import numpy as _np
import vtk as _vtk
import copy as _copy 
import pyg4ometry.transformation as _transformation
import logging as _log

class VtkViewer : 
    def __init__(self,size=(1024,768)) : 
        
        # create a renderer
        self.ren = _vtk.vtkRenderer()
        
        # create a rendering window
        self.renWin = _vtk.vtkRenderWindow()
        self.renWin.AddRenderer(self.ren)

        # create a rendering window interactor 
        self.iren = _vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.renWin)

        self.ren.SetBackground(1.0, 1.0, 1.0)
        self.renWin.SetSize(*size)

        # local meshes 
        self.localmeshes = {}
        self.localmeshesOverlap = {}

        # filters (per mesh)
        self.filters = {}
        self.filtersOverlap = {}
        
        # mappers (per mesh) 
        self.mappers = []
        self.physicalMapperMap = {}
        self.mappersOverlap = []
        self.physicalMapperMapOverlap = {}

        # actors (per placement) 
        self.actors = []
        self.physicalActorMap = {}
        self.actorsOverlap = [] 
        self.physicalActorMapOverlap = {}

    def addLocalMesh(self, meshName, mesh) : 
        pass

    def addMeshInstance(self, meshName, placementName, placement) : 
        # Filter? Like triangle filter? 
        # Mapper? 
        
        pass

    def addLogicalVolume(self, logical, mrot = _np.matrix([[1,0,0],[0,1,0],[0,0,1]]), tra = _np.array([0,0,0])) :
        _log.info('VtkViewer.addLogicalVolume> %s' % (logical.name))

        for pv in logical.daughterVolumes : 
            _log.info('VtkViewer.addLogicalVolume> Daughter %s %s %s ' % (pv.name, pv.logicalVolume.name, pv.logicalVolume.solid.name))
            
            # pv transform 
            pvmrot  = _transformation.tbxyz2matrix(pv.rotation.eval())
            pvtra   = _np.array(pv.position.eval())

            # pv compound transform 
            new_mrot = mrot*pvmrot
            new_tra  = (_np.array(mrot.dot(pvtra)) + tra)[0]
  
            # get the local vtkPolyData 
            _log.info('VtkViewer.addLogicalVolume> vtkPD')
            solidname = pv.logicalVolume.solid.name
            try : 
                vtkPD = self.localmeshes[solidname]
            except KeyError : 
                localmesh = pv.logicalVolume.mesh.localmesh
                vtkPD     = pycsgMeshToVtkPolyData(localmesh)
                self.localmeshes[solidname] = vtkPD

            # get the local overlap vtkPolyData
            try : 
                vtkPDOverlap = self.localmeshesOverlap[solidname] 
            except KeyError : 
                localmeshOverlap = pv.logicalVolume.mesh.overlapmeshes
                vtkPDOverlap = [] 
                for mol in localmeshOverlap : 
                    vtkPDOverlap.append(pycsgMeshToVtkPolyData(mol))
                    self.localmeshesOverlap[solidname] = vtkPDOverlap

            # triangle filter    
            _log.info('VtkViewer.addLogicalVolume> vtkFLT')
            filtername = solidname+"_filter"
            try : 
                vtkFLT = self.filters[filtername] 
            except KeyError :  
                vtkFLT = _vtk.vtkTriangleFilter()
                vtkFLT.AddInputData(vtkPD)
                # vtkFLT.Update()
                self.filters[filtername] = vtkFLT

            # triangle filters for overlaps 
            try : 
                vtkFLTOverlap = self.filtersOverlap[filtername] 
            except KeyError : 
                self.filtersOverlap[filtername] = []
                for pdo in vtkPDOverlap : 
                    vtkFLTOverlap = _vtk.vtkTriangleFilter()
                    vtkFLTOverlap.AddInputData(pdo)
                    self.filtersOverlap[filtername].append(vtkFLTOverlap)
            
            # mapper 
            _log.info('VtkViewer.addLogicalVolume> vtkMAP')

            mappername = solidname+"_mapper" 
            vtkMAP = _vtk.vtkPolyDataMapper()
            vtkMAP.ScalarVisibilityOff()
            vtkMAP.SetInputConnection(vtkFLT.GetOutputPort())
            self.mappers.append(vtkMAP)

            # mapper for overlaps 
            vtkMAPOverlaps = [] 
            for flt in self.filtersOverlap[filtername] :                 
                vtkMAPOverlap = _vtk.vtkPolyDataMapper() 
                vtkMAPOverlap.ScalarVisibilityOff()
                vtkMAPOverlap.SetInputConnection(flt.GetOutputPort())
                self.mappersOverlap.append(vtkMAPOverlap)
                vtkMAPOverlaps.append(vtkMAPOverlap)
            
            # mapper look up dictionary 
            try : 
                self.physicalMapperMap[pv.name].append(vtkMAP)
            except KeyError : 
                self.physicalMapperMap[pv.name] = [vtkMAP]
            
            # actor
            _log.info('VtkViewer.addLogicalVolume> vtkActor')

            actorname = pv.name+"_actor"             
            vtkActor = _vtk.vtkActor() 

            # store actor (need to increment count if exists)
            self.actors.append(vtkActor)
            
            # actor look up dictionary
            try : 
                self.physicalActorMap[pv.name].append(vtkActor)
            except KeyError : 
                self.physicalActorMap[pv.name] = [vtkActor]

            vtkActor.SetMapper(vtkMAP)        

            rotaa = _transformation.matrix2axisangle(new_mrot)

            vtkActor.SetPosition(new_tra[0],new_tra[1],new_tra[2])
            vtkActor.RotateWXYZ(rotaa[1]/_np.pi*180.0,rotaa[0][0],rotaa[0][1],rotaa[0][2])
            vtkActor.GetProperty().SetColor(1,0,0)
            
            _log.info('VtkViewer.addLogicalVolume> Add actor')
            self.ren.AddActor(vtkActor)

            # actors for overlaps 
            for m in vtkMAPOverlaps : 
                vtkActorOverlap = _vtk.vtkActor() 
                self.actorsOverlap.append(vtkActorOverlap)
                vtkActorOverlap.SetMapper(m)
                vtkActorOverlap.SetPosition(new_tra[0],new_tra[1],new_tra[2])
                vtkActorOverlap.RotateWXYZ(rotaa[1]/_np.pi*180.0,rotaa[0][0],rotaa[0][1],rotaa[0][2])
                vtkActorOverlap.GetProperty().SetColor(1,0,0)
                self.ren.AddActor(vtkActorOverlap)

            self.addLogicalVolume(pv.logicalVolume,new_mrot,new_tra)

        
    def view(self):
        # enable user interface interactor
        # self.iren.Initialize()

        # Camera setup
        camera =_vtk.vtkCamera();
        self.ren.SetActiveCamera(camera);
        self.ren.ResetCamera()

        # Render 
        self.renWin.Render()

        self.iren.Start()    
        
# python iterable to vtkIdList
def mkVtkIdList(it):
    vil = _vtk.vtkIdList()
    for i in it:
        vil.InsertNextId(int(i))
    return vil

# convert pycsh mesh to vtkPolyData
def pycsgMeshToVtkPolyData(mesh) : 

    # refine mesh 
    # mesh.refine()

    verts, cells, count = mesh.toVerticesAndPolygons()
    meshPolyData = _vtk.vtkPolyData() 
    points       = _vtk.vtkPoints()
    polys        = _vtk.vtkCellArray()
    scalars      = _vtk.vtkFloatArray()

    for v in verts :
        points.InsertNextPoint(v)

    for p in cells :
        polys.InsertNextCell(mkVtkIdList(p))

    for i in range(0,count) :
        scalars.InsertTuple1(i,1)

    meshPolyData.SetPoints(points)
    meshPolyData.SetPolys(polys)
    meshPolyData.GetPointData().SetScalars(scalars)

    del points
    del polys
    del scalars
        
    return meshPolyData

def writeVtkPolyDataAsSTLFile(fileName, meshes) :
# Convert vtkPolyData to STL mesh
    ''' meshes : list of triFilters '''

    appendFilter = _vtk.vtkAppendPolyData()

    for m in meshes:
        if m :
            appendFilter.AddInputConnection(m.GetOutputPort())

    # append mesh to filter
    appendFilter.Update()

    # remove duplicate points
    cleanFilter = _vtk.vtkCleanPolyData()
    cleanFilter.SetInputConnection(appendFilter.GetOutputPort())
    cleanFilter.Update()

    # write STL file
    print 'stlWriter'
    stlWriter = _vtk.vtkSTLWriter()
    print 'setFileName'
    stlWriter.SetFileName(fileName)
    print 'inputConnection'
    stlWriter.SetInputConnection(appendFilter.GetOutputPort())
    print 'write'
    stlWriter.Write()
    print 'done'
    return stlWriter