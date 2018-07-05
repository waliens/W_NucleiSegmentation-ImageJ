FROM neubiaswg5/fiji-base

RUN mkdir /plugins

RUN cd plugins && wget -O imagescience.jar https://imagescience.org/meijering/software/download/imagescience.jar
RUN cd plugins && wget -O FeatureJ_.jar https://imagescience.org/meijering/software/download/FeatureJ_.jar

WORKDIR /app
RUN pip install scikit-image

ADD macro.ijm /app/macros/macro.ijm
ADD run.sh /app/run.sh
ADD wrapper.py /app/wrapper.py
# TODO move into a proper AnnotationImporter module
ADD mask_to_objects.py /app/mask_to_objects.py

RUN cd /app && chmod a+x run.sh

ENTRYPOINT ["python", "wrapper.py"]
