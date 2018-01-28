# Run the metrics-macro in ImageJ headlessly using Xvfb to avoid errors due to ImageJ1 gui dependencies.

export DISPLAY=:2
Xvfb $DISPLAY -auth /dev/null &
(
# the '(' starts a new sub shell. In this sub shell we start the worker processes:

java -Xmx6000m -cp /fiji/jars/ij-1.51s.jar ij.ImageJ -headless --console -macro NucleiSegmentation-ImageJ.ijm "input=$1, output=$2, radius=$3, threshold=$4"
wait # waits until all 'program' processes are finished
# this wait sees only the 'program' processes, not the Xvfb process
)
