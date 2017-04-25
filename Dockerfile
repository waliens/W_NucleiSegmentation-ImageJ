FROM baecker/fiji-base:latest

RUN cd plugins && wget -O imagescience.jar https://imagescience.org/meijering/software/download/imagescience.jar
RUN cd plugins && wget -O FeatureJ_.jar https://imagescience.org/meijering/software/download/FeatureJ_.jar

RUN cd /fiji/macros && wget -O IJSegmentClusteredNuclei.ijm https://gist.githubusercontent.com/volker-baecker/d1c973c9b8e60afa537206f515f89964/raw/f15ce41efb15b14a7c53255d6a31475718269328/IJSegmentClusteredNuclei.ijm
RUN cd /fiji && wget -O run-segment-clustered-nuclei.sh https://gist.githubusercontent.com/volker-baecker/dd6544ed91d940224df48192dd2cc947/raw/ab88f44a55410956b2b86f6c11c287c7da58a6ba/run-segment-clustered-nuclei.sh && chmod a+x run-segment-clustered-nuclei.sh
