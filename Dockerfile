# AWSM is built on SMRF
FROM usdaarsnwrc/smrf:0.9

MAINTAINER Scott Havens <scott.havens@ars.usda.gov>

####################################################
# Software version
####################################################
ENV VPYSNOBAL "0.2.0"

####################################################
# Install dependencies
####################################################

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get install -y texlive-base \
    && apt-get install -y texlive-lang-english \
    && apt-get install -y texlive-latex-extra \
    && cd /code \
    && curl -L https://github.com/USDA-ARS-NWRC/pysnobal/archive/v${VPYSNOBAL}.tar.gz | tar xz \
    && rm -rf /var/lib/apt/lists/* \
    && apt remove -y curl \
    && apt autoremove -y

####################################################
# AWSM
####################################################

COPY . / /code/awsm/

#ENV PYTHONPATH=/code/awsm/

RUN cd /code/pysnobal-${VPYSNOBAL} \
    && python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements_smrf.txt \
    && python3 setup.py install \
    && cd /code/awsm \
    && python3 -m pip install -r /code/awsm/requirements.txt \
    && python3 setup.py install \
    && python3 setup.py install \
    && rm -r /root/.cache/pip

WORKDIR /data

COPY ./docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
RUN echo "umask 0002" >> /etc/bash.bashrc
ENTRYPOINT ["/docker-entrypoint.sh"]
#CMD ["python3", "/code/awsm/scripts/awsm"]

#ENTRYPOINT ["python3", "/code/awsm/scripts/awsm"]
