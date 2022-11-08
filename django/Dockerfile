FROM python:3.9-buster

# The enviroment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

# create root directory for our project in the container
RUN mkdir /django

# create scrapy subdir
RUN mkdir /django/scraper

# Pip dependency Twisted needs gcc
RUN apt-get update
RUN apt-get install -y gcc

# Set the working directory to /django
WORKDIR /django


# Install miniconda to /miniconda
RUN curl -LO https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh
RUN bash Miniconda3-py39_4.9.2-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda3-py39_4.9.2-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

RUN conda install -c conda-forge spacy==2.3.2 &&\
 conda install -c conda-forge spacy-model-en_core_web_lg=2.3.1=pyh9f0ad1d_0

#RUN python -m spacy download en_core_web_lg
# Install needed packages specified in requirements.txt
ADD ./requirements.txt .

RUN pip install -r requirements.txt

# Version
ARG APP_VERSION
ENV APP_VERSION "$APP_VERSION"

# Copy App
COPY . .

RUN chmod +x start.sh
