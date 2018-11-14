import os
import sys
from subprocess import call

from cytomine import CytomineJob
from cytomine.models import Job

from neubiaswg5.metrics import computemetrics_batch
from neubiaswg5.cytomine import prepare_data, upload_data, upload_metrics


def main(argv):
    # 0. Initialize Cytomine client and job
    with CytomineJob.from_cli(argv) as cj:
        cj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")

        problem_cls = "ObjSeg"

        # 1. Create working directories on the machine
        # 2. Download the images
        in_images, gt_images, in_path, gt_path, out_path, tmp_path = prepare_data(problem_cls, cj)

        # 3. Call the image analysis workflow using the run script
        cj.job.update(progress=25, statusComment="Launching workflow...")
        command = "/usr/bin/xvfb-run java -Xmx6000m -cp /fiji/jars/ij.jar ij.ImageJ --headless --console " \
                  "-macro macro.ijm \"input={}, output={}, radius={}, threshold={}\"".format(in_path, out_path, cj.parameters.ij_radius, cj.parameters.ij_threshold)
        return_code = call(command, shell=True, cwd="/fiji")  # waits for the subprocess to return

        if return_code != 0:
            err_desc = "Failed to execute the ImageJ macro (return code: {})".format(return_code)
            cj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)

        # 4. Upload the annotation and labels to Cytomine
        upload_data(problem_cls, cj, in_images, out_path,
                    start=60, end=90, period=0.1, prefix="Extracting and uploading polygons from masks")

        # 5. Compute and upload the metrics
        cj.job.update(progress=90, statusComment="Computing and uploading metrics...")
        upload_metrics(problem_cls, cj, in_images, gt_path, out_path, tmp_path)

        # 6. End
        cj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
