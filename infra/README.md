# Ayna local infrastructure

`compose.yaml` defines PostgreSQL, Redis, private MinIO, one-shot migration/storage setup,
API, RQ worker and Vite web services. Only web/API and the local MinIO console bind to
loopback. Database, Redis and object APIs are private to the Compose network.
The documented example passwords are local development defaults. Supply private values
and disable the development seller-header shortcut before deployment. Cookie-backed
seller/admin authentication is implemented; HTTPS, private secrets and merchant service
configuration are still deployment requirements.
