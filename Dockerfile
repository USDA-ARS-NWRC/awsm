# AWSM is built on SMRF
FROM scotthavens/smrf:latest

MAINTAINER Scott Havens <scott.havens@ars.usda.gov>

####################################################
# Install dependencies
####################################################

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && cd /code \
    && curl -L https://github.com/USDA-ARS-NWRC/pysnobal/archive/master.tar.gz | tar xz \
    && rm -rf /var/lib/apt/lists/* \
    && apt remove -y curl \
    && apt autoremove -y

####################################################
# AWSM
####################################################

COPY . / /code/awsm/

RUN cd /code/pysnobal-master \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements_dev.txt \
    && python3 setup.py install \
    && cd /code/awsm \
    && python3 -m pip install -r /code/awsm/requirements_dev.txt \
    && python3 setup.py install \
    && rm -r /root/.cache/pip

WORKDIR /data

ENTRYPOINT ["/bin/bash"]
