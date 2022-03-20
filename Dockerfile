FROM python:3.8 AS builder

RUN pip install -U pip setuptools wheel
RUN pip install pdm

COPY . /mapsplat/

WORKDIR /mapsplat
RUN pdm install --prod --no-lock --no-editable

FROM python:3.8

ENV PYTHONPATH=/mapsplat/pkgs
COPY --from=builder /mapsplat/__pypackages__/3.8/lib /project/pkgs

ENTRYPOINT ["python", "-m", "project"]