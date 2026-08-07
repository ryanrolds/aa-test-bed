# Thin image on top of the published Alliance Auth image that installs the
# plugins this test bed exercises, from PyPI. Versions are pinned in
# conf/aa/requirements.txt; changing that file means rebuilding the image:
#   docker compose up -d --build
#
# Build context is the repo root (see docker-compose.yml), so COPY paths below
# are relative to the repo root.
ARG AA_DOCKER_TAG
FROM ${AA_DOCKER_TAG}

USER root
COPY --chown=allianceauth:allianceauth conf/aa/requirements.txt /aa-plugins/requirements.txt

USER allianceauth
RUN pip install --no-cache-dir -r /aa-plugins/requirements.txt
