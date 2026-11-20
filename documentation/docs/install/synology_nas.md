# Synology NAS

AdventureLog runs on a Synology NAS with Container Manager (Docker).

## Install

Marius Hosting has a step-by-step guide: [How to install AdventureLog on your Synology NAS](https://mariushosting.com/how-to-install-adventurelog-on-your-synology-nas/).

The guide is maintained outside the AdventureLog project. You can also follow [Standard Deployment](standard.md) with Container Manager's **Project** feature, which accepts the same `docker-compose.yml`.

## 502 Bad Gateway

On recent versions of DSM, the built-in reverse proxy may return **502 Bad Gateway**. Marius Hosting explains the fix: [Synology nginx reverse proxy: how to fix 502 Bad Gateway](https://mariushosting.com/synology-nginx-reverse-proxy-how-to-fix-502-bad-gateway-error/).

## Next steps

- [First Steps](first_steps.md): sign in, secure the admin account, and decide who can join.
