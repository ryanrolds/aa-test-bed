# Thin image on top of the published Alliance Auth image that installs this
# repo's plugin(s) in editable mode. Combined with the runtime bind-mount of
# ./plugins/wanderer-leaderboard, editing plugin source + restarting is enough
# to pick up changes — no rebuild unless dependencies change.
#
# Build context is the repo root (see docker-compose.yml), so COPY paths below
# are relative to the repo root.
ARG AA_DOCKER_TAG
FROM ${AA_DOCKER_TAG}

USER root
COPY --chown=allianceauth:allianceauth plugins/wanderer-leaderboard /aa-plugins/wanderer-leaderboard
COPY --chown=allianceauth:allianceauth conf/aa/requirements.txt /aa-plugins/requirements.txt

USER allianceauth
RUN pip install --no-cache-dir -e /aa-plugins/wanderer-leaderboard \
    && pip install --no-cache-dir -r /aa-plugins/requirements.txt
