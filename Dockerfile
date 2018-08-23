# AWSM is built on SMRF
FROM usdaarsnwrc/smrf:develop

MAINTAINER Scott Havens <scott.havens@ars.usda.gov>

####################################################
# Install dependencies
####################################################

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get install -y texlive-base \
    && apt-get install -y texlive-lang-english \
    && apt-get install -y texlive-latex-extra \
    && cd /code \
    && curl -L https://github.com/USDA-ARS-NWRC/pysnobal/archive/master.tar.gz | tar xz \
    && curl -L https://github.com/USDA-ARS-NWRC/snowav/archive/master.tar.gz | tar xz \
    && rm -rf /var/lib/apt/lists/* \
    && apt remove -y curl \
    && apt autoremove -y

####################################################
# AWSM
####################################################

COPY . / /code/awsm/

#ENV PYTHONPATH=/code/awsm/

RUN cd /code/pysnobal-master \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements_smrf.txt \
    && python3 setup.py install \
    && cd /code/awsm \
    && python3 -m pip install -r /code/awsm/requirements.txt \
    && python3 setup.py install \
    && cd /code/snowav-master \
    && python3 -m pip install -r /code/snowav-master/requirements.txt \
    && python3 setup.py install \
    && rm -r /root/.cache/pip

WORKDIR /data

COPY ./docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
#CMD ["python3", "/code/awsm/scripts/awsm"]

#ENTRYPOINT ["python3", "/code/awsm/scripts/awsm"]
