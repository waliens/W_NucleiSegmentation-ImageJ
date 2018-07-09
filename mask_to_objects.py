# -*- coding: utf-8 -*-
from functools import partial
from warnings import warn

import cv2
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import explain_validity
from shapely.affinity import affine_transform as aff_transfo
from skimage.measure import points_in_poly, label as label_fn


class ObjectSlice(object):
    """Represent a slice of an object"""
    def __init__(self, polygon, label, time=None, depth=None):
        self._polygon = polygon
        self._label = label
        self._time = time
        self._depth = depth

    @property
    def polygon(self):
        return self._polygon

    @property
    def label(self):
        return self._label

    @property
    def time(self):
        return self._time

    @property
    def depth(self):
        return self._depth


def affine_transform(xx_coef=1, xy_coef=0, yx_coef=0, yy_coef=1,
                     delta_x=0, delta_y=0):
    """
    Represents a 2D affine transformation:
    x' = xx_coef * x + xy_coef * y + delta_x
    y' = yx_coef * x + yy_coef * y + delta_y
    Constructor parameters
    ----------------------
    xx_coef: float (default: 1)
        The x from x coefficient
    xy_coef: float (default: 0)
        The x from y coefficient
    yx_coef: float (default: 0)
        The y from x coefficient
    yy_coef: float (default: 1)
        The y from y coefficient
    delta_x: float (default: 0)
        The translation over x-axis
    delta_y: float (default: 0)
        The translation over y-axis
    Return
    ------
    affine_transformer : callable: shapely.Geometry => shapely.Geometry
        The function representing the 2D affine transformation
    """
    return partial(aff_transfo, matrix=[xx_coef, xy_coef, yx_coef, yy_coef,
                                        delta_x, delta_y])


def identity(x):
    """Identity function
    Parameters
    ----------
    x: T
        The object to return
    Returns
    -------
    x: T
        The passed object
    """
    return x


def geom_as_list(geometry):
    """Return the list of sub-polygon a polygon is made up of"""
    if geometry.geom_type == "Polygon":
        return [geometry]
    elif geometry.geom_type == "MultiPolygon":
        return geometry.geoms


def linear_ring_is_valid(ring):
    points = set([(x, y) for x, y in ring.coords])
    return len(points) >= 3


def fix_geometry(geometry):
    """Attempts to fix an invalid geometry (from https://goo.gl/nfivMh)"""
    try:
        return geometry.buffer(0)
    except ValueError:
        pass

    polygons = geom_as_list(geometry)

    fixed_polygons = list()
    for i, polygon in enumerate(polygons):
        if not linear_ring_is_valid(polygon.exterior):
            continue

        interiors = []
        for ring in polygon.interiors:
            if linear_ring_is_valid(ring):
                interiors.append(ring)

        fixed_polygon = Polygon(polygon.exterior, interiors)

        try:
            fixed_polygon = fixed_polygon.buffer(0)
        except ValueError:
            continue

        fixed_polygons.extend(geom_as_list(fixed_polygon))

    if len(fixed_polygons) > 0:
        return MultiPolygon(fixed_polygons)
    else:
        return None


def _locate(segmented, offset=None):
    """Inspired from: https://goo.gl/HYPrR1"""
    # CV_RETR_EXTERNAL to only get external contours.
    _, contours, hierarchy = cv2.findContours(segmented.copy(),
                                              cv2.RETR_CCOMP,
                                              cv2.CHAIN_APPROX_SIMPLE)

    # Note: points are represented as (col, row)-tuples apparently
    transform = identity
    if offset is not None:
        col_off, row_off = offset
        transform = affine_transform(delta_x=col_off, delta_y=row_off)
    components = []
    if len(contours) > 0:
        top_index = 0
        tops_remaining = True
        while tops_remaining:
            exterior = contours[top_index][:, 0, :].tolist()

            interiors = []
            # check if there are childs and process if necessary
            if hierarchy[0][top_index][2] != -1:
                sub_index = hierarchy[0][top_index][2]
                subs_remaining = True
                while subs_remaining:
                    interiors.append(contours[sub_index][:, 0, :].tolist())

                    # check if there is another sub contour
                    if hierarchy[0][sub_index][0] != -1:
                        sub_index = hierarchy[0][sub_index][0]
                    else:
                        subs_remaining = False

            # add component tuple to components only if exterior is a polygon
            if len(exterior) > 3:
                polygon = Polygon(exterior, interiors)
                polygon = transform(polygon)
                if polygon.is_valid:  # some polygons might be invalid
                    components.append(polygon)
                else:
                    fixed = fix_geometry(polygon)
                    if fixed.is_valid:
                        components.append(fixed)
                    else:
                        warn("Attempted to fix invalidity '{}' in polygon but failed... "
                             "Output polygon still invalid '{}'".format(explain_validity(polygon),
                                                                        explain_validity(fixed)))

            # check if there is another top contour
            if hierarchy[0][top_index][0] != -1:
                top_index = hierarchy[0][top_index][0]
            else:
                tops_remaining = False

    del contours
    del hierarchy
    return components


def get_polygon_inner_point(polygon):
    """
    Algorithm:
        1) Take a point on the exterior boundary
        2) Find an adjacent point (with digitized coordinates) that lies in the polygon
        3) Return the coordinates of this point

    Parameters
    ----------
    polygon: Polygon
        The polygon

    Returns
    -------
    point: tuple
        (x, y) coordinates for the found points. x and y are integers.
    """
    exterior = polygon.exterior.coords
    for x, y in exterior:  # usually this function will return in one iteration
        neighbours = np.array(neighbour_pixels(int(x), int(y)))
        in_poly = np.array(points_in_poly(list(neighbours), exterior))
        if np.count_nonzero(in_poly) > 0:  # make sure at least one point is in the polygon
            return neighbours[in_poly][0]
    raise ValueError("No points could be found inside the polygon ({}) !".format(polygon.wkt))


def neighbour_pixels(x, y):
    """Get the neigbours pixel of x and y"""
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y    ), (x, y    ), (x + 1, y    ),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1)
    ]


def mask_to_objects_2d(mask, background=0, offset=None):
    """Convert 2D (binary or label) mask to polygons.

    Parameters
    ----------
    mask: ndarray
        2D mask array. Expected shape: (height, width).
    background: int
        Value used for encoding background pixels.
    offset: tuple (optional, default: None)
        (x, y) coordinate offset to apply to all the extracted polygons.

    Returns
    -------
    extracted: list of ObjectSlice
        Each object slice represent an object from the image. Fields time and depth of ObjectSlice are set to None.

    Notes
    -----
    Adjacent but distinct polygons must be separated by at least one line of background (e.g. value 0) pixels.
    The mask array is not modified by the function.
    """
    if mask.ndim != 2:
        raise ValueError("Cannot handle image with ndim different from 2 ({} dim. given).".format(mask.ndim))
    # opencv only supports contour extraction for binary masks
    mask_cpy = np.zeros(mask.shape, dtype=np.uint8)
    mask_cpy[mask != background] = 255
    # extract polygons and labels
    polygons = _locate(mask_cpy, offset=offset)
    objects = list()
    for polygon in polygons:
        x, y = get_polygon_inner_point(polygon)
        objects.append(ObjectSlice(polygon=polygon, label=mask[y, x]))
    return objects


def mask_to_objects_3d(mask, background=0, offset=None, assume_unique_labels=False, time=False):
    """Convert a 3D or 2D+t (binary or label) mask to polygon slices.

    Parameters
    ----------
    mask: ndarray
        3D mask array. Expected shape: (width, height, depth|time).
    background: int
        Value used for encoding background pixels.
    offset: tuple (optional, default (0, 0, 0))
        A (x, y, z) offset to apply to all the detected objects.
    assume_unique_labels: bool
        True if each objects is encoded with a unique label in the mask.
    time: bool
        True if the image is a 2D+t volume, false if it is a 3D volume.
    Returns
    -------
    objects: list
        Lists all the extracted objects. Each object is provided as a list of slices (i.e. python object of type
        ObjectSlice). A slice consists of a 2D polygon, a label and the depth or time at which it was taken.
        If time is True, the field depth of ObjectSlice is set to None. Otherwise, the field time is set to None.
    """
    if mask.ndim != 3:
        raise ValueError("Cannot handle image with ndim different from 3 ({} dim. given).".format(mask.ndim))
    label_img = mask if assume_unique_labels else label_fn(mask, connectivity=2, background=background)
    height, width, depth = label_img.shape

    # extract slice per slice
    offset_xy = offset[:2]
    offset_z = offset[-1]
    objects = dict()  # maps object label with list of slices (as object_3d_type objects)
    for d in range(depth):
        slice_objects = mask_to_objects_2d(label_img[:, :, d], background, offset=offset_xy)
        for slice_object in slice_objects:
            x, y = get_polygon_inner_point(slice_object.polygon)
            label = slice_object.label
            objects[label] = objects.get(label, []) + [
                ObjectSlice(
                    polygon=slice_object.polygon,
                    label=mask[y, x, d],
                    depth=d + offset_z if not time else None,
                    time=d + offset_z if time else None
                )
            ]
    return objects.values()


def mask_to_objects_3dt(mask, background=0, offset=None):
    """Convert a 3D+t label mask to polygon slices.

    Parameters
    ----------
    mask: ndarray
        4D mask array. Expected shape: (time, height, width, depth).
    background: int
        Value used for encoding background pixels.
    offset: tuple (optional, default (0, 0, 0, 0))
        A (t, x, y, z) offset to apply to all the detected objects.

    Returns
    -------
    objects: list
        Lists all the extracted objects in a three-level list. Third level lists the slices of an object at a given
        timestep. The second level lists all the timesteps at which an object appears and the first level lists all the
        objects.
        E.g.:
        - P_i_j_k denotes the polygon in the kth slice at the jth time for object i
        - t_i_j denotes the jth timestep for object i
        - s_i_j_k denotes the kth slice of object i at the jth time
        - label_i denotes the label of the object i

        [ # objects
            [ # timesteps (object 1)
                [ # slices (object 1, timestep 1)
                    ObjectSlice(P_1_1_1, t_1_1, s_1_1_1, label_1),
                    ObjectSlice(P_1_1_2, t_1_1, s_1_1_2, label_1),
                 ...],
                [ # slices (object 1, timestep 2)
                    ObjectSlice(P_1_2_1, t_1_2, s_1_2_1, label_1),
                    ObjectSlice(P_1_2_2, t_1_2, s_1_2_2, label_1),
                 ...],
                ...
            ],
            [ # timesteps (object 2)
                [ # slices (object 2, timestep 1)
                    ObjectSlice(P_2_1_1, t_2_1, s_2_1_1, label_2),
                    ObjectSlice(P_2_1_2, t_2_1, s_2_1_2, label_2),
                 ...],
                [ # slices (object 2, timestep 2)
                    ObjectSlice(P_2_2_1, t_2_2, s_2_2_1, label_2),
                    ObjectSlice(P_2_2_2, t_2_2, s_2_2_2, label_2),
                 ...],
                ...
            ]
        ]

    Notes
    -----
    Each object should be encoded with the same label over time.
    """
    if mask.ndim != 4:
        raise ValueError("Cannot handle image with ndim different from 4 ({} dim. given).".format(mask.ndim))
    duration = mask.shape[0]
    offset_xyz = offset[1:]
    offset_t = offset[0]
    objects = dict()
    for t in range(duration):
        time_objects = mask_to_objects_3d(
            mask,
            background=background,
            offset=offset_xyz,
            assume_unique_labels=True,
            time=False
        )
        for time_slices in time_objects:
            label = time_slices[0].label
            slices_3dt = [  # transform type of objects to
                ObjectSlice(
                    polygon=s.polygon,
                    label=s.label,
                    depth=s.depth,
                    time=t + offset_t
                ) for s in time_slices
            ]
            objects[label] = objects.get(label, []) + [slices_3dt]
    return objects.values()
