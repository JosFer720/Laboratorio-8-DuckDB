# CC3084 - Lab 8: DuckDB
# Ambiente reproducible para Python, DuckDB y JupyterLab.
FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    JUPYTER_PLATFORM_DIRS=1

RUN groupadd --gid 1000 lab \
 && useradd --uid 1000 --gid lab --create-home --shell /bin/bash lab

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN python -m pip install --requirement /workspace/requirements.txt \
 && chown -R lab:lab /workspace

USER lab

EXPOSE 8888

CMD ["jupyter", "lab", \
     "--ip=0.0.0.0", \
     "--port=8888", \
     "--no-browser", \
     "--ServerApp.root_dir=/workspace", \
     "--ServerApp.token=", \
     "--ServerApp.password="]
