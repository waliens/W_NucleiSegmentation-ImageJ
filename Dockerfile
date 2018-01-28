FROM neubiaswg5/fiji-base:latest

RUN cd plugins && wget -O imagescience.jar https://imagescience.org/meijering/software/download/imagescience.jar
RUN cd plugins && wget -O FeatureJ_.jar https://imagescience.org/meijering/software/download/FeatureJ_.jar

ADD NucleiSegmentation-ImageJ.ijm /fiji/macros/NucleiSegmentation-ImageJ.ijm                                           
ADD run-segment-clustered-nuclei.sh /fiji/run-segment-clustered-nuclei.sh
RUN cd /fiji && chmod a+x run-segment-clustered-nuclei.sh

ENTRYPOINT ["/bin/sh", "run-segment-clustered-nuclei.sh"]
