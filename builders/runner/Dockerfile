FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3

RUN python -m pip install --no-cache-dir \
    build==1.2.2.post1 \
    packaging==26.3 \
    pyproject-hooks==1.3.3 \
    setuptools==75.6.0 \
    wheel==0.45.1

WORKDIR /src
