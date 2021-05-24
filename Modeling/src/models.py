import os
import numpy as np
import sys
import vtk
import utils
import label_io

class Geometry(object):
    def __init__(self, vtk_poly, edge_size=1.):
        self.poly = vtk_poly
        self.edge_size = edge_size
    def getVolume(self):
        return utils.getPolydataVolume(self.poly)

    def writeSurfaceMesh(self, fn):
        label_io.writeVTKPolyData(self.poly, fn)
    
    def writeVolumeMesh(self, fn):
        label_io.writeVTUFile(self.ug, fn)

    def splitRegion(self, region_id, attr='ModelFaceID'):
        return utils.thresholdPolyData(self.poly, attr, (region_id, region_id))
    
    def remesh(self, edge_size, fn, poly_fn=None, ug_fn=None, mmg=True):
        import meshing
        self.edge_size = edge_size
        if mmg:
            meshing.remeshPolyData(self.poly, 1., 1.5)
        self.writeSurfaceMesh(fn)
        # generate volumetric mesh:
        mesh_ops = {
                'surface_mesh_flag': True,
                'volume_mesh_flag': True,
                'global_edge_size': edge_size, 
        }
        if poly_fn is None:
            mesh_ops['surface_mesh_flag']=False
        if ug_fn is None:
            mesh_ops['surface_mesh_flag']=False
        surface, volume = meshing.meshPolyData(fn, mesh_ops, (poly_fn, ug_fn))
        if surface is not None:
            self.poly = surface
        if volume is not None:
            self.ug = volume
        return 
    def writeMeshComplete(self, path):

        pass


class leftHeart(Geometry):
    
    def __init__(self, vtk_poly, edge_size=1.):
        super(leftHeart, self).__init__(vtk_poly, edge_size)
        self.wall_processed = False
        self.cap_processed = False
        self.cap_pts_ids = None

    def processWall(self, aa_cutter, aa_plane):
        if self.wall_processed:
            print("Left heart  wall has been processed!")
            return
        self.poly = utils.cutPolyDataWithAnother(self.poly, aa_cutter,aa_plane)
        self.poly = utils.fillHole(self.poly, size=25.)
        id_lists,boundaries = utils.getPointIdsOnBoundaries(self.poly)
        for idx, (ids, boundary) in enumerate(zip(id_lists, boundaries)):
            boundary = utils.smoothVTKPolyline(boundary, 5)
            self.poly = utils.projectOpeningToFitPlane(self.poly, ids, boundary.GetPoints(), self.edge_size)
            # Remove the free cells and update the point lists
            self.poly, id_lists[idx] = utils.removeFreeCells(self.poly, [idx for sub_l in id_lists for idx in sub_l])
        self.poly = utils.smoothVTKPolydata(utils.cleanPolyData(self.poly, 0.), iteration=50)
        self.wall_processed = True
        return
    def processCap(self, edge_size):
        if self.cap_processed:
            print("Caps have been processed!")
            return
        self.poly = utils.capPolyDataOpenings(self.poly, edge_size)
        self.cap_processed = True
        return
    
class leftVentricle(Geometry):
    
    def __init__(self, vtk_poly, edge_size=1.):
        super(leftVentricle, self).__init__(vtk_poly, edge_size)
        self.wall_processed = False
        self.cap_processed = False
        self.cap_pts_ids = None

    def processWall(self, la_cutter, la_plane, aa_cutter, aa_plane):
        if self.wall_processed:
            print("Left ventricle wall has been processed!")
            return
        # cut with la and aorta cutter:
        self.poly = utils.cutPolyDataWithAnother(self.poly, la_cutter, la_plane)
        self.poly = utils.cutPolyDataWithAnother(self.poly, aa_cutter, aa_plane)
        #fill small cutting artifacts:
        self.poly = utils.fillHole(self.poly, size=15.)
        #improve valve opening geometry
        id_lists,boundaries = utils.getPointIdsOnBoundaries(self.poly)
        for idx, (ids, boundary) in enumerate(zip(id_lists, boundaries)):
            boundary = utils.smoothVTKPolyline(boundary, 5)
            self.poly = utils.projectOpeningToFitPlane(self.poly, ids, boundary.GetPoints(), self.edge_size)
            # Remove the free cells and update the point lists
            self.poly, id_lists[idx] = utils.removeFreeCells(self.poly, [idx for sub_l in id_lists for idx in sub_l])
        self.poly = utils.smoothVTKPolydata(utils.cleanPolyData(self.poly, 0.), iteration=50)
        
        self.wall_processed = True
        return

    def processCap(self, edge_size):
        if self.cap_processed:
            print("Caps have been processed!")
            return
        self.poly = utils.capPolyDataOpenings(self.poly, edge_size)
        self.cap_processed = True
        return


    def getCapIds(self):
        self.cap_pts_ids = list()
        # good to assume region id mitral=2, aortic=3
        for cap_id in (2,3):
            self.cap_pts_ids.append(utils.findPointCorrespondence(self.poly, self.splitRegion(cap_id).GetPoints()))
   
   
    def update(self, new_model):
        if self.cap_pts_ids is None:
            self.getCapIds()
        # Project the cap points so that they are co-planar
        for pt_ids in self.cap_pts_ids:
            pts = utils.getPolyDataPointCoordinatesFromIDs(new_model, pt_ids)
            new_model = utils.projectOpeningToFitPlane(new_model, pt_ids, pts, self.edge_size)
        return new_model

    def writeMeshComplete(self, path):
        """
        Args: 
            path: path to the output folder
        """
        if (self.poly is None) or (self.ug is None):
            raise RuntimeError("No volume mesh has been generated.")
            return
        
        try:
            os.makedirs(os.path.join(path))
        except Exception as e: print(e)
        
        fn_poly = os.path.join(path, 'mesh-complete.exterior.vtp')
        fn_vol = os.path.join(path, 'mesh-complete.mesh.vtu')
        self.writeVolumeMesh(fn_vol)
        self.writeSurfaceMesh(fn_poly)

        fn_wall = os.path.join(path, 'walls_combined.vtp')
        label_io.writeVTKPolyData(self.splitRegion(1),fn_wall)
        try:
            os.makedirs(os.path.join(path, 'mesh-surfaces'))
        except Exception as e: print(e)

        for i in range(3):
            face = self.splitRegion(i+1)
            face_fn = os.path.join(path,'mesh-surfaces','noname_%d.vtp' % (i+1))
            label_io.writeVTKPolyData(face, face_fn)
        return

        


