FROM python:3.10-slim

WORKDIR /tmp

# install dependencies (without [dev] and [huggingface] extra libs)
COPY setup.py setup.py
COPY README.md README.md
COPY streamlit_rag/requirements.txt streamlit_requirements.txt

# Multi-stage preparation
# remove extra lib from setup.py, generate list of needed libs and install them
RUN sed -i '/extras_require={/,/}/d' setup.py && \ 
    python3 setup.py egg_info && \
    pip install -r goldenverba.egg-info/requires.txt && \
    pip install -r streamlit_requirements.txt

# now install Verba and steramlit client
WORKDIR /Verba

COPY requirements.txt /Verba/requirements.txt
COPY setup.py /Verba/setup.py
COPY README.md /Verba/README.md
COPY goldenverba /Verba/goldenverba
COPY streamlit_rag/ /Verba/streamlit_rag/
COPY docker-chatbot.sh /Verba/docker-chatbot.sh 

RUN chmod +x /Verba/docker-chatbot.sh && \
    pip3 install --no-cache-dir --no-deps -e . && \
    pip3 install --no-cache-dir --no-deps -e streamlit_rag/. 

RUN apt-get -y update; apt-get -y install curl





