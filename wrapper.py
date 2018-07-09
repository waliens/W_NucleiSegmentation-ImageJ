import os
import sys
from subprocess import call

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


def main(argv):
    # 0. Initialize Cytomine client and job
    with CytomineJob.from_cli(argv) as cj:
        cj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")

        # 1. Create working directories on the machine:
        # - WORKING_PATH/in: input images
        # - WORKING_PATH/out: output images
        # - WORKING_PATH/ground_truth: ground truth images
        base_path = "{}".format(os.getenv("HOME"))
        gt_suffix = "_lbl"
        working_path = os.path.join(base_path, str(cj.job.id))
        in_path = os.path.join(working_path, "in")
        out_path = os.path.join(working_path, "out")
        gt_path = os.path.join(working_path, "ground_truth")

        if not os.path.exists(working_path):
            os.makedirs(working_path)
            os.makedirs(in_path)
            os.makedirs(out_path)
            os.makedirs(gt_path)

        # 2. Download the images (first input, then ground truth image)
        cj.job.update(progress=1, statusComment="Downloading images (to {})...".format(in_path))
        image_instances = ImageInstanceCollection().fetch_with_filter("project", cj.parameters.cytomine_id_project)
        input_images = [i for i in image_instances if gt_suffix not in i.originalFilename]
        gt_images = [i for i in image_instances if gt_suffix in i.originalFilename]

        for input_image in input_images:
            input_image.download(os.path.join(in_path, "{id}.tif"))

        for gt_image in gt_images:
            related_name = gt_image.originalFilename.replace(gt_suffix, '')
            related_image = [i for i in input_images if related_name == i.originalFilename]
            if len(related_image) == 1:
                gt_image.download(os.path.join(gt_path, "{}.tif".format(related_image[0].id)))

        # 3. Call the image analysis workflow using the run script
        cj.job.update(progress=25, statusComment="Launching workflow...")
        command = "/bin/sh /app/run.sh {} {} {} {}".format(in_path, out_path, cj.parameters.radius, cj.parameters.threshold)
        return_code = call(command, shell=True)  # waits for the subprocess to return

        if return_code != 0:
            err_desc = "Failed to execute the ImageJ macro (return code: {})".format(return_code)
            cj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)

        # 4. Upload the annotation and labels to Cytomine (annotations are extracted from the mask using
        # the AnnotationExporter module)
        for image in cj.monitor(input_images, start=60, end=80, period=0.1, prefix="Extracting and uploading polygons from masks"):
            file = "{}.tif".format(image.id)
            path = os.path.join(out_path, file)
            data = io.imread(path)

            # extract objects
            slices = mask_to_objects_2d(data)

            print("Found {} polygons in this image {}.".format(len(slices), image.id))

            # upload
            for obj_slice in slices:
                annotation = Annotation(
                    location=obj_slice.polygon.wkt, id_image=image.id,
                    id_project=cj.parameters.cytomine_id_project
                )
                annotation.save()
                if annotation:
                    Property(annotation, "index", str(obj_slice.label)).save()

        # 5. Compute the metrics
        cj.job.update(progress=80, statusComment="Computing metrics...")

        # TODO: compute metrics:
        # in /out: output files {id}.tiff
        # in /ground_truth: label files {id}.tiff

        cj.job.update(progress=99, statusComment="Cleaning...")
        for image in input_images:
            os.remove(os.path.join(in_path, "{}.tif".format(image.id)))

        cj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
