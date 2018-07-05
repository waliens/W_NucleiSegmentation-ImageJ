import logging
import os
import sys
from argparse import ArgumentParser
from subprocess import call, PIPE

from cytomine import CytomineJob
from cytomine.models import Annotation, AnnotationTerm, Job, ImageInstanceCollection, Property
from shapely.affinity import affine_transform
from skimage import io

from mask_to_objects import mask_to_objects_2d


def add_annotation(img_inst, polygon, label=None, proba=1.0):
    image_id = img_inst.id
    # Transform in cartesian coordinates
    polygon = affine_transform(polygon, [1, 0, 0, -1, 0, img_inst.height])

    annotation = Annotation(polygon.wkt, image_id).save()
    if label is not None and annotation is not None:
        annotation_term = AnnotationTerm()
        annotation_term.annotation = annotation.id
        annotation_term.annotationIdent = annotation.id
        annotation_term.userannotation = annotation.id
        annotation_term.term = label
        annotation_term.expectedTerm = label
        annotation_term.rate = proba
        annotation_term.save()
    return annotation


def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


def relative_progress(current, _min, _max):
    return int(_min + current * (_max - _min))


parser = ArgumentParser(prog="IJSegmentClusteredNuclei", description="ImageJ workflow to segment clustered nuclei")
parser.add_argument('--cytomine_host', dest="cytomine_host", required=True)
parser.add_argument('--cytomine_public_key', dest="cytomine_public_key", required=True)
parser.add_argument('--cytomine_private_key', dest="cytomine_private_key", required=True)
parser.add_argument('--cytomine_id_project', dest="cytomine_id_project", required=True)
parser.add_argument('--cytomine_id_software', dest="cytomine_id_software", required=True)
parser.add_argument("--ij_radius,", dest="radius", default="5")
parser.add_argument('--ij_threshold', dest="threshold", default="-0.5")
params, others = parser.parse_known_args(sys.argv)

base_path = "/dockershare/"
gt_suffix = "_lbl"

with CytomineJob(params.cytomine_host, params.cytomine_public_key, params.cytomine_private_key,
                 params.cytomine_id_software, params.cytomine_id_project, verbose=logging.INFO) as cj:
    cj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")

    working_path = os.path.join(base_path, str(cj.job.id))
    in_path = os.path.join(working_path, "in")
    makedirs(in_path)
    out_path = os.path.join(working_path, "out")
    makedirs(out_path)
    gt_path = os.path.join(working_path, "ground_truth")
    makedirs(gt_path)

    cj.job.update(progress=1, statusComment="Downloading images (to {})...".format(in_path))
    image_instances = ImageInstanceCollection().fetch_with_filter("project", params.cytomine_id_project)
    input_images = [i for i in image_instances if gt_suffix not in i.originalFilename]
    gt_images = [i for i in image_instances if gt_suffix in i.originalFilename]

    for input_image in input_images:
        input_image.download(os.path.join(in_path, "{id}.tif"))

    for gt_image in gt_images:
        related_name = gt_image.originalFilename.replace(gt_suffix, '')
        related_image = [i for i in input_images if related_name == i.originalFilename]
        if len(related_image) == 1:
            gt_image.download(os.path.join(gt_path, "{}.tif".format(related_image[0].id)))

    # call the image analysis workflow in the docker image
    cj.job.update(progress=25, statusComment="Launching workflow...")
    command = "/bin/sh /app/run.sh /app/data/in /app/data/out {} {}".format(params.radius, params.threshold)
    code = call(command, shell=True)  # waits for the subprocess to return

    for image in cj.monitor(input_images, start=60, end=80, period=0.1, prefix="Extracting and uploading polygons from masks"):
        file = "{}.tif".format(image.id)
        path = os.path.join(out_path, file)
        data = io.imread(path)

        # extract objects
        objects = mask_to_objects_2d(data)

        print("Found {} polygons in this image {}.".format(len(objects), image.id))

        # upload
        for object in objects:
            annotation = add_annotation(image, object.polygon)
            if annotation:
                Property(annotation, "index", str(object.label)).save()

    cj.job.update(progress=80, statusComment="Computing metrics...")

    # TODO: compute metrics:
    # in /out: output files {id}.tiff
    # in /ground_truth: label files {id}.tiff

    cj.job.update(progress=99, statusComment="Cleaning...")
    for image in input_images:
        os.remove(os.path.join(in_path, "{}.tif".format(image.id)))

    cj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")
