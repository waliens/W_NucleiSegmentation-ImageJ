# IJSegmentClusteredNuclei
Segment clustered nuclei using a laplacian filter, thresholding and a binary watershed transform

use 
docker run -v $(pwd):/fiji/data IJSegmentClusteredNuclei /bin/sh -c "run-segment-clustered-nuclei.sh input=data/in output=data/out radius=5 threshold=-0.5"

to run the docker image.
