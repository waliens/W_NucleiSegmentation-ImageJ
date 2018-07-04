FROM cytomineuliege/software-python3-base

RUN apt-get update
RUN apt-get install -y curl
# Install Xvfb (X virtual frame buffer)
RUN apt-get install -y xvfb
RUN apt-get install -y libx11-dev libxtst-dev # libXrender-dev

# add webupd8 repository
RUN \
    echo "===> add webupd8 repository..."  && \
    echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee /etc/apt/sources.list.d/webupd8team-java.list  && \
    echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list  && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys EEA14886  && \
    apt-get update  && \
    \
    \
    echo "===> install Java"  && \
    echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections  && \
    echo debconf shared/accepted-oracle-license-v1-1 seen true | debconf-set-selections  && \
    DEBIAN_FRONTEND=noninteractive  apt-get install -y --force-yes oracle-java8-installer oracle-java8-set-default  && \
    \
    \
    echo "===> clean up..."  && \
    rm -rf /var/cache/oracle-jdk8-installer  && \
    apt-get clean  && \
rm -rf /var/lib/apt/lists/*

# Define working directory.
WORKDIR /app

# Install Fiji.
RUN \
      curl -O http://update.imagej.net/bootstrap.js && \
      jrunscript bootstrap.js update-force-pristine

# Add fiji to the PATH
ENV PATH $PATH:/app

RUN mkdir /app/data

# Define default command.
CMD ["fiji-linux64"]

RUN cd plugins && wget -O imagescience.jar https://imagescience.org/meijering/software/download/imagescience.jar
RUN cd plugins && wget -O FeatureJ_.jar https://imagescience.org/meijering/software/download/FeatureJ_.jar

RUN pip install numpy opencv-python-headless scikit-image shapely

ADD macro.ijm /app/macros/macro.ijm
ADD run.sh /app/run.sh
ADD wrapper.py /app/wrapper.py
ADD mask_to_objects.py /app/mask_to_objects.py
RUN cd /app && chmod a+x run.sh

ENTRYPOINT ["python", "wrapper.py"]
