# Local-development Fuseki: the upstream image plus a dev-bundle Shiro config
# that opens the admin endpoints so the web UI's dataset list and Graph Store
# writes work through Docker's published port. The upstream default restricts
# /$/** to localhost, which hangs the UI on "Loading…" and 401s the loader when
# Fuseki is reached through a port mapping.
#
# The entrypoint copies this template into the data volume on first init and
# runs envsubst to inject ADMIN_PASSWORD, so the ${ADMIN_PASSWORD} placeholder
# in shiro.ini is filled at container start.
FROM stain/jena-fuseki:latest

COPY shiro.ini /jena-fuseki/shiro.ini
