import os
import numpy as np
import sys
import vtk
import utils
import io_utils

class Geometry(object):
    def __init__(self, vtk_poly, edge_size=1.):
        self.poly = vtk_poly
        self.edge_size = edge_size
    def get_volume(self):
        return utils.get_polydata_volume(self.poly)

    def write_surface_mesh(self, fn):
        io_utils.write_vtk_polydata(self.poly, fn)
    
    def write_volume_mesh(self, fn):
        io_utils.write_vtu_file(self.ug, fn)

    def split_region(self, region_id, attr='ModelFaceID'):
        return utils.threshold_polydata(self.poly, attr, (region_id, region_id))
    
    def remesh(self, edge_size, fn, poly_fn=None, ug_fn=None, mmg=True):
        import meshing
        self.edge_size = edge_size
        if mmg:
            meshing.remesh_polydata(self.poly, 1., 1.5)
        self.write_surface_mesh(fn)
        # generate volumetric mesh:
        mesh_ops = {
                'surface_mesh_flag': True,
                'volume_mesh_flag': True,
                'global_edge_size': edge_size, 
        }
        surface, volume = meshing.mesh_polydata(fn, mesh_ops, (poly_fn, ug_fn))
        if surface is not None:
            self.poly = surface
        if volume is not None:
            self.ug = volume
        return 
    def write_mesh_complete(self, path):

        pass


class LeftHeart(Geometry):
    
    def __init__(self, vtk_poly, edge_size=1.):
        super(LeftHeart, self).__init__(vtk_poly, edge_size)
        self.wall_processed = False
        self.cap_processed = False
        self.cap_pts_ids = None

    def process_wall(self, aa_cutter, aa_plane):
        if self.wall_processed:
            print("Left heart  wall has been processed!")
            return
        self.poly = utils.cut_polydata_with_another(self.poly, aa_cutter,aa_plane)
        self.poly = utils.fill_hole(self.poly, size=25.)
        id_lists,boundaries = utils.get_point_ids_on_boundaries(self.poly)
        for idx, (ids, boundary) in enumerate(zip(id_lists, boundaries)):
            boundary = utils.smooth_vtk_polyline(boundary, 5)
            self.poly = utils.project_opening_to_fit_plane(self.poly, ids, boundary.GetPoints(), self.edge_size)
            # Remove the free cells and update the point lists
            self.poly, id_lists[idx] = utils.remove_free_cells(self.poly, [idx for sub_l in id_lists for idx in sub_l])
        self.poly = utils.smooth_vtk_polydata(utils.clean_polydata(self.poly, 0.), iteration=50)
        self.wall_processed = True
        return
    def process_cap(self, edge_size):
        if self.cap_processed:
            print("Caps have been processed!")
            return
        self.poly = utils.cap_polydata_openings(self.poly, edge_size)
        self.cap_processed = True
        return
    
class LeftVentricle(Geometry):
    
    def __init__(self, vtk_poly, edge_size=1.):
        super(LeftVentricle, self).__init__(vtk_poly, edge_size)
        self.wall_processed = False
        self.cap_processed = False
        self.cap_pts_ids = None

    def process_wall(self, la_cutter, la_plane, aa_cutter, aa_plane):
        if self.wall_processed:
            print("Left ventricle wall has been processed!")
            return
        # cut with la and aorta cutter:
        self.poly = utils.cut_polydata_with_another(self.poly, la_cutter, la_plane)
        self.poly = utils.cut_polydata_with_another(self.poly, aa_cutter, aa_plane)
        #fill small cutting artifacts:
        self.poly = utils.fill_hole(self.poly, size=15.)
        #improve valve opening geometry
        id_lists,boundaries = utils.get_point_ids_on_boundaries(self.poly)
        for idx, (ids, boundary) in enumerate(zip(id_lists, boundaries)):
            boundary = utils.smooth_vtk_polyline(boundary, 5)
            self.poly = utils.project_opening_to_fit_plane(self.poly, ids, boundary.GetPoints(), self.edge_size)
            # Remove the free cells and update the point lists
            self.poly, id_lists[idx] = utils.remove_free_cells(self.poly, [idx for sub_l in id_lists for idx in sub_l])
        self.poly = utils.smooth_vtk_polydata(utils.clean_polydata(self.poly, 0.), iteration=50)
        
        self.wall_processed = True
        return

    def process_cap(self, edge_size):
        if self.cap_processed:
            print("Caps have been processed!")
            return
        self.poly = utils.cap_polydata_openings(self.poly, edge_size)
        self.cap_processed = True
        return


    def get_cap_ids(self):
        self.cap_pts_ids = list()
        # good to assume region id mitral=2, aortic=3
        for cap_id in (2,3):
            self.cap_pts_ids.append(utils.find_point_correspondence(self.poly, self.split_region(cap_id).GetPoints()))
   
   
    def update(self, new_model):
        if self.cap_pts_ids is None:
            self.get_cap_ids()
        # Project the cap points so that they are co-planar
        for pt_ids in self.cap_pts_ids:
            pts = utils.get_polydata_point_coordinates_from_ids(new_model, pt_ids)
            new_model = utils.project_opening_to_fit_plane(new_model, pt_ids, pts, self.edge_size)
        return new_model

    def write_mesh_complete(self, path):
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
        self.write_volume_mesh(fn_vol)
        self.write_surface_mesh(fn_poly)

        fn_wall = os.path.join(path, 'walls_combined.vtp')
        io_utils.write_vtk_polydata(self.split_region(1),fn_wall)
        try:
            os.makedirs(os.path.join(path, 'mesh-surfaces'))
        except Exception as e: print(e)

        for i in range(3):
            face = self.split_region(i+1)
            face_fn = os.path.join(path,'mesh-surfaces','noname_%d.vtp' % (i+1))
            io_utils.write_vtk_polydata(face, face_fn)
        return

        


