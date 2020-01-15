import pyg4ometry.transformation as _transformation
import pyg4ometry.fluka as _fluka
from pyg4ometry.fluka.directive import rotoTranslationFromTra2 as _rotoTranslationFromTra2
import numpy as _np
import copy as _copy

def geant4Logical2Fluka(logicalVolume) :
    rotation = _np.array([0,0,0])
    position = _np.array([0,0,0])
    scale    = _np.array([1,1,1])

    flukaRegistry = _fluka.FlukaRegistry()

    flukaNameCount = 0

    # find extent of logical
    extent = logicalVolume.extent(includeBoundingSolid = True)

    # create black body body
    blackBody = _fluka.RPP("BLKBODY",
                           2*extent[0][0]/10,2*extent[1][0]/10,
                           2*extent[0][1]/10,2*extent[1][1]/10,
                           2*extent[0][2]/10,2*extent[1][2]/10,
                           transform=_rotoTranslationFromTra2("BBROTDEF",[rotation,position], flukaregistry=flukaRegistry),
                           flukaregistry=flukaRegistry)

    fzone = _fluka.Zone()
    fzone.addIntersection(blackBody)

    # create top logical volume
    flukaMotherOuterRegion, flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,logicalVolume.solid,rotation,position,scale,flukaRegistry)
    flukaMotherRegion      = _copy.deepcopy(flukaMotherOuterRegion)
    flukaNameCount += 1

    for zone in flukaMotherOuterRegion.zones :
        fzone.addSubtraction(zone)

    for dv in logicalVolume.daughterVolumes :

        newposition = position + _np.array(dv.position.eval())
        newrotation = _transformation.matrix2tbxyz(_transformation.tbxyz2matrix(_np.array(dv.rotation.eval())).dot(_transformation.tbxyz2matrix(-rotation)))

        flukaDaughterOuterRegion, flukaNameCount = geant4PhysicalVolume2Fluka(dv,newrotation,newposition,scale,flukaRegistry,flukaNameCount)

        # subtract daughters from black body
        for motherZones in flukaMotherRegion.zones :
            for daughterZones in flukaDaughterOuterRegion.zones :
                motherZones.addSubtraction(daughterZones)


    # create black body region
    fregion = _fluka.Region("BLKHOLE")
    fregion.addZone(fzone)
    flukaRegistry.addRegion(fregion)

    flukaRegistry.addRegion(flukaMotherRegion)

    return flukaRegistry

def geant4PhysicalVolume2Fluka(physicalVolume,
                               rotation = [0,0,0],position = [0,0,0], scale = [1,1,1],
                               flukaRegistry=None,flukaNameCount=0) :

    # logical volume (outer and complete)
    geant4LvOuterSolid = physicalVolume.logicalVolume.solid
    # print 'g2fPhysicalVolume',physicalVolume.name, flukaName, flukaNameCount, rotation, position, scale
    flukaMotherOuterRegion, flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,geant4LvOuterSolid,
                                                                     rotation,position,scale,
                                                                     flukaRegistry)
    flukaMotherRegion      = _copy.deepcopy(flukaMotherOuterRegion)


    # loop over daughers and remove from mother region
    for dv in physicalVolume.logicalVolume.daughterVolumes :

        # placement information for daughter
        newposition = position + _transformation.tbxyz2matrix(rotation).dot(_np.array(dv.position.eval()))
        newrotation = _transformation.matrix2tbxyz(_transformation.tbxyz2matrix(_np.array(rotation)).dot(_transformation.tbxyz2matrix(-_np.array(dv.rotation.eval()))))

        flukaDaughterOuterRegion, flukaNameCount = geant4PhysicalVolume2Fluka(dv,rotation=newrotation,position=newposition,scale=scale,flukaRegistry=flukaRegistry, flukaNameCount=flukaNameCount)

        for motherZones in flukaMotherRegion.zones:
            for daughterZones in flukaDaughterOuterRegion.zones:
                motherZones.addSubtraction(daughterZones)

    flukaRegistry.addRegion(flukaMotherRegion)

    return flukaMotherOuterRegion, flukaNameCount

def geant4Solid2FlukaRegion(flukaNameCount,solid, rotation = [0,0,0], position = [0,0,0], scale = [1,1,1], flukaRegistry = None, addRegistry = True) :

    import pyg4ometry.gdml.Units as _Units  # TODO move circular import

    name = format(flukaNameCount,'04')

    fregion = None
    fbodies = []


    transform=_rotoTranslationFromTra2("T"+name,[rotation,position],flukaregistry=flukaRegistry)

    # print 'geant4Solid2FlukaRegion',flukaNameCount,name,solid.type, rotation,position,transform

    if solid.type == 'Box' :
        uval = _Units.unit(solid.lunit)/10.
        pX = solid.evaluateParameter(solid.pX)*uval/2
        pY = solid.evaluateParameter(solid.pY)*uval/2
        pZ = solid.evaluateParameter(solid.pZ)*uval/2.0

        fbody = _fluka.RPP("B"+name+'_01', -pX, pX, -pY, pY, -pZ, pZ,
                           transform=transform,
                           flukaregistry=flukaRegistry,
                           addRegistry=True)

        # store all bodies
        fbodies.append(fbody)

        # create zones and region
        fzone = _fluka.Zone()
        fzone.addIntersection(fbody)
        fregion = _fluka.Region("R"+name)
        fregion.addZone(fzone)

        flukaNameCount += 1

    elif solid.type == "Tubs":

        uval = _Units.unit(solid.lunit)/10.
        aval = _Units.unit(solid.aunit)

        pRMin = solid.evaluateParameter(solid.pRMin)*uval
        pSPhi = solid.evaluateParameter(solid.pSPhi)*aval
        pDPhi = solid.evaluateParameter(solid.pDPhi)*aval
        pDz   = solid.evaluateParameter(solid.pDz)*uval
        pRMax = solid.evaluateParameter(solid.pRMax)*uval

        # main cylinder
        fbody1 = _fluka.ZCC("B"+name+"_01",0,0,pRMax,
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # low z cut
        fbody2 = _fluka.XYP("B"+name+"_02",-pDz/2,
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # high z cut
        fbody3 = _fluka.XYP("B"+name+"_03", pDz/2,transform=transform,
                            flukaregistry=flukaRegistry)

        # inner cylinder
        if pRMin != 0 :
            fbody4 = _fluka.ZCC("B"+name+"_04",0,0,pRMin,
                                transform=transform,
                                flukaregistry=flukaRegistry)

        # phi cuts
        if pDPhi != 2*_np.pi :
            fbody5 = _fluka.PLA("B"+name+"_05",
                                [_np.sin(pSPhi),_np.cos(pSPhi),0],
                                [0, 0, 0],
                                transform=transform,
                                flukaregistry=flukaRegistry)

            fbody6 = _fluka.PLA("B"+name+"_06",
                                [_np.sin(pSPhi+pDPhi),_np.cos(pSPhi+pDPhi),0],
                                [0, 0, 0],
                                transform=transform,
                                flukaregistry=flukaRegistry)


        fzone = _fluka.Zone()
        fzone.addIntersection(fbody1)
        fzone.addSubtraction(fbody2)
        fzone.addIntersection(fbody3)

        if pRMin != 0 :
            fzone.addSubtraction(fbody4)


        if pDPhi != 2*_np.pi :
            fzone1 = _fluka.Zone()
            fzone1.addIntersection(fbody5)
            fzone1.addIntersection(fbody6)
            fzone.addSubtraction(fzone1)

        fregion = _fluka.Region("R"+name)
        fregion.addZone(fzone)

        flukaNameCount += 1

    elif solid.type == "CutTubs" :

        uval = _Units.unit(solid.lunit)/10
        aval = _Units.unit(solid.aunit)

        pRMin = solid.evaluateParameter(solid.pRMin)*uval
        pSPhi = solid.evaluateParameter(solid.pSPhi)*aval
        pDPhi = solid.evaluateParameter(solid.pDPhi)*aval
        pDz   = solid.evaluateParameter(solid.pDz)*uval
        pRMax = solid.evaluateParameter(solid.pRMax)*uval
        pLowNorm0  = solid.evaluateParameter(solid.pLowNorm[0])
        pLowNorm1  = solid.evaluateParameter(solid.pLowNorm[1])
        pLowNorm2  = solid.evaluateParameter(solid.pLowNorm[2])
        pHighNorm0 = solid.evaluateParameter(solid.pHighNorm[0])
        pHighNorm1 = solid.evaluateParameter(solid.pHighNorm[1])
        pHighNorm2 = solid.evaluateParameter(solid.pHighNorm[2])

        # main cylinder
        fbody1 = _fluka.ZCC("B"+name+"_01",0,0,pRMax,
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # low z cut
        fbody2 = _fluka.PLA("B"+name+"_02",
                            [-pLowNorm0,-pLowNorm1,-pLowNorm2],
                            [0, 0, -pDz/2],
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # high z cut
        fbody3 = _fluka.PLA("B"+name+"_03",
                            [pHighNorm0,pHighNorm1,pHighNorm2],
                            [0, 0, pDz/2.],
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # inner cylinder
        fbody4 = _fluka.ZCC("B"+name+"_04",0,0,pRMin,
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # phi cuts
        fbody5 = _fluka.PLA("B"+name+"_05",
                            [_np.sin(pSPhi),_np.cos(pSPhi),0],
                            [0, 0, 0],
                            transform=transform,
                            flukaregistry=flukaRegistry)

        fbody6 = _fluka.PLA("B"+name+"_06",
                            [_np.sin(pSPhi+pDPhi),_np.cos(pSPhi+pDPhi),0],
                            [0, 0, 0],
                            transform=transform,
                            flukaregistry=flukaRegistry)

        fzone = _fluka.Zone()
        fzone.addIntersection(fbody1)
        fzone.addSubtraction(fbody2)
        fzone.addIntersection(fbody3)

        fzone.addSubtraction(fbody4)

        fzone1 = _fluka.Zone()
        fzone1.addIntersection(fbody5)
        fzone1.addIntersection(fbody6)

        fzone.addSubtraction(fzone1)

        fregion = _fluka.Region("R"+name)
        fregion.addZone(fzone)

        flukaNameCount += 1

    elif solid.type == "EllipticalTube":
        uval = _Units.unit(solid.lunit)/10.

        pDx = solid.evaluateParameter(solid.pDx)*uval
        pDy = solid.evaluateParameter(solid.pDy)*uval
        pDz = solid.evaluateParameter(solid.pDz)*uval

        # main elliptical cylinder
        fbody1 = _fluka.ZEC("B"+name+"_01",
                            0,0,
                            pDx,
                            pDy,
                            transform=transform,
                            flukaregistry=flukaRegistry)

        # low z cut
        fbody2 = _fluka.XYP("B"+name+"_02",-pDz/2,transform=transform,
                            flukaregistry=flukaRegistry)

        # high z cut
        fbody3 = _fluka.XYP("B"+name+"_03", pDz/2,transform=transform,
                            flukaregistry=flukaRegistry)

        fzone = _fluka.Zone()
        fzone.addIntersection(fbody1)
        fzone.addSubtraction(fbody2)
        fzone.addIntersection(fbody3)

        fregion = _fluka.Region("R"+name)
        fregion.addZone(fzone)

        flukaNameCount += 1

    elif solid.type == "Sphere" :
        pass
    elif solid.type == "Orb" :
        pass
    elif solid.type == "EllipticalCone" :
        pass

    elif solid.type == "ExtrudedSolid":
        # create low z end plane
        # create high z end plane
        # loop over z planes

        # loop over xy points

        pass

    elif solid.type == "Union":
        # build both solids to regions
        # take zones from 2 and add as zones to 1

        rot = solid.tra2[0]
        pos = solid.tra2[1]

        solid1 = solid.obj1
        solid2 = solid.obj2

        position2 = position + _transformation.tbxyz2matrix(rotation).dot(_np.array(pos.eval()))
        rotation2 = _transformation.matrix2tbxyz(_transformation.tbxyz2matrix(_np.array(rotation)).dot(_transformation.tbxyz2matrix(-_np.array(rot.eval()))))

        r1,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid1,rotation , position ,[1,1,1],flukaRegistry,False)
        r2,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid2,rotation2, position2,[1,1,1],flukaRegistry,False)

        fregion = _fluka.Region("R"+name)

        for zone in r1.zones:
            fregion.addZone(zone)

        for zone in r2.zones:
            fregion.addZone(zone)

    elif solid.type == "Subtraction":
        # build both solids to regions
        # take zones from 2 and distribute over zones of 1

        rot = solid.tra2[0]
        pos = solid.tra2[1]

        solid1 = solid.obj1
        solid2 = solid.obj2

        position2 = position + _transformation.tbxyz2matrix(rotation).dot(_np.array(pos.eval()))
        rotation2 = _transformation.matrix2tbxyz(_transformation.tbxyz2matrix(_np.array(rotation)).dot(_transformation.tbxyz2matrix(-_np.array(rot.eval()))))

        r1,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid1,rotation , position ,[1,1,1],flukaRegistry,False)
        r2,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid2,rotation2, position2,[1,1,1],flukaRegistry,False)

        fregion = _fluka.Region("R"+name)

        for zone1 in r1.zones:
            for zone2 in r2.zones:
                zone1.addSubtraction(zone2)
            fregion.addZone(zone1)

    elif solid.type == "Intersection":
        # build both zones to regions
        # take zones from 2 and distribute over zones of 1

        # build both solids to regions
        # take zones from 2 and distribute over zones of 1

        rot = solid.tra2[0]
        pos = solid.tra2[1]

        solid1 = solid.obj1
        solid2 = solid.obj2

        position2 = position + _transformation.tbxyz2matrix(rotation).dot(_np.array(pos.eval()))
        rotation2 = _transformation.matrix2tbxyz(_transformation.tbxyz2matrix(_np.array(rotation)).dot(_transformation.tbxyz2matrix(-_np.array(rot.eval()))))

        r1,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid1,rotation , position ,[1,1,1],flukaRegistry,False)
        r2,flukaNameCount = geant4Solid2FlukaRegion(flukaNameCount,solid2,rotation2, position2,[1,1,1],flukaRegistry,False)

        fregion = _fluka.Region("R"+name)

        for zone1 in r1.zones:
            for zone2 in r2.zones:
                zone1.addIntersection(zone2)
            fregion.addZone(zone1)

    else :
        print solid.type
    return fregion, flukaNameCount

