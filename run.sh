# Run the metrics-macro in ImageJ headlessly using Xvfb to avoid errors due to ImageJ1 gui dependencies.

cd /fiji && ./ImageJ-linux64 --headless --console -macro macro.ijm "input=$1, output=$2, radius=$3, threshold=$4"
