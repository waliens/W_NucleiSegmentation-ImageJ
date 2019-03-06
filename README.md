# IJSegmentClusteredNuclei
Segment clustered nuclei using a laplacian filter, thresholding and a binary watershed transform

use 
docker run -v $(pwd):/fiji/data ijsegmentclusterednuclei /bin/sh -c "run-segment-clustered-nuclei.sh data/in data/out 5 -0.5"

to run the docker image.

The parameters are the input folder, the output folder, the radius of the laplacian filter and the threshold value.

## Integration with NEUBIAS web-based database of bioimage analysis tools 
This workflow is described in [www.biii.eu](www.biii.eu) in [http://biii.eu/nuclei-segmentation-2d-imagej](http://biii.eu/nuclei-segmentation-2d-imagej)
