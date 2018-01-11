# AWSM is built on SMRF
FROM scotthavens/smrf:latest

MAINTAINER Scott Havens <scott.havens@ars.usda.gov>

####################################################
# Install dependencies
####################################################

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && cd /code \
    && curl -L https://github.com/USDA-ARS-NWRC/pysnobal/archive/py3fix.tar.gz | tar xz \
    && rm -rf /var/lib/apt/lists/* \
    && apt remove -y curl \
    && apt autoremove -y

####################################################
# AWSM
####################################################

COPY . / /code/AWSM/

RUN cd /code/pysnobal-py3fix \
    && pip3 install -r requirements_dev.txt \
    && python3 setup.py install \
    && cd /code/AWSM \
    && pip3 install -r /code/AWSM/requirements_dev.txt \
    && python3 setup.py install \
    && rm -r /root/.cache/pip

WORKDIR /data

ENTRYPOINT ["/bin/bash"]









