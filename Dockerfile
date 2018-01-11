# SMRF is built on the IPW
FROM scotthavens/ipw:latest

MAINTAINER Scott Havens <scott.havens@ars.usda.gov>

####################################################
# System requirements
####################################################

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libffi-dev \
    libssl-dev \
    libyaml-dev \
    libfreetype6-dev \
    libpng-dev \
    libhdf5-serial-dev \
    python3-dev \
    python3-pip \
    python3-wheel \
    python3-tk \
    curl \
    libgrib-api-dev \
    && cd /code \
    && curl -L https://github.com/USDA-ARS-NWRC/weather_forecast_retrieval/archive/v0.3.2.tar.gz | tar xz \
    && rm -rf /var/lib/apt/lists/* \
    && apt remove -y curl \
    && apt autoremove -y

####################################################
# SMRF
####################################################

COPY . / /code/smrf/

RUN mkdir /data \
    && cd /code/smrf \
    && pip3 install -r /code/smrf/requirements.txt \
    && python3 setup.py install \
    && cd /code/weather_forecast_retrieval-0.3.2 \
    && pip3 install pyproj==1.9.5.1 \
    && pip3 install -r requirements_dev.txt \
    && python3 setup.py install \
    && rm -r /root/.cache/pip

####################################################
# Create a shared data volume
####################################################

VOLUME /data
WORKDIR /data

ENTRYPOINT ["/bin/bash"]









