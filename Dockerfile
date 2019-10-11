# python:3.6.9-stretch
FROM python@sha256:62e7985e22c4265d8f656295aca9d9307e83d6a5fa9ae673a68d60fc43d41158

# ---------------------------------------------------------------------------------------------------------------------
# Install Java
RUN apt-get update && apt-get install openjdk-8-jdk -y && apt-get clean

# ---------------------------------------------------------------------------------------------------------------------
# Install Cytomine python client
RUN git clone https://github.com/cytomine-uliege/Cytomine-python-client.git
RUN cd /Cytomine-python-client && git checkout tags/v2.3.0.poc && pip install .
RUN rm -r /Cytomine-python-client

# ---------------------------------------------------------------------------------------------------------------------
# Fiji installation
# Install virtual X server
RUN apt-get update && apt-get install -y unzip xvfb libx11-dev libxtst-dev libxrender-dev

# Install Fiji.
RUN wget https://downloads.imagej.net/fiji/Life-Line/fiji-linux64-20170530.zip
RUN unzip fiji-linux64-20170530.zip
RUN mv Fiji.app/ fiji

# create a sym-link with the name jars/ij.jar that is pointing to the current version jars/ij-1.nm.jar
RUN cd /fiji/jars && ln -s $(ls ij-1.*.jar) ij.jar

# Add fiji to the PATH
ENV PATH $PATH:/fiji
RUN mkdir -p /fiji/data

# Clean up
RUN rm fiji-linux64-20170530.zip

# ---------------------------------------------------------------------------------------------------------------------
# Install Neubias-W5-Utilities (annotation exporter, compute metrics, helpers,...)
RUN git clone https://github.com/Neubias-WG5/neubiaswg5-utilities.git
RUN cd /neubiaswg5-utilities/ && git checkout tags/v0.7.0.poc && pip install .

# install utilities binaries
RUN chmod +x /neubiaswg5-utilities/bin/*
RUN cp /neubiaswg5-utilities/bin/* /usr/bin/

# cleaning
RUN rm -r /neubiaswg5-utilities

# ---------------------------------------------------------------------------------------------------------------------
# Install Fiji plugins
RUN cd /fiji/plugins && wget -O imagescience.jar https://imagescience.org/meijering/software/download/imagescience.jar
RUN cd /fiji/plugins && wget -O FeatureJ_.jar https://imagescience.org/meijering/software/download/FeatureJ_.jar

# ---------------------------------------------------------------------------------------------------------------------
# Install Macro
ADD macro.ijm /fiji/macros/macro.ijm
ADD wrapper.py /app/wrapper.py

# for running the wrapper locally
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python", "/app/wrapper.py"]
