# mzdpilot backend: konik, not Comma Connect

mzdpilot does not talk to Comma Connect. Drive upload and remote access go to
[konik](https://konik.ai/) instead. If konik is unreachable, the device runs
normally and uploads nothing. It never falls back to comma.

## What the device contacts

| Purpose | Host |
|---|---|
| API (registration, upload URLs) | `https://api.konik.ai` |
| Remote control websocket | `wss://athena.konik.ai` |
| Pairing QR / web app | `https://stable.konik.ai` |

Both hosts are code defaults (`openpilot/common/api/comma_connect.py`,
`openpilot/system/athena/athenad.py`). Set `API_HOST` and `ATHENA_HOST` to
point a device at your own [connect-killer](https://github.com/MoreTore/connect-killer)
instance.

## First boot after the switch

A one-shot params migration (`openpilot/sunnypilot/system/params_migration.py`):

- deletes the comma-issued `DongleId` (param and `/persist/comma/dongle_id`),
  so the device registers at `api.konik.ai` on the same boot;
- turns sunnylink off (`SunnylinkEnabled`), so no footage goes to
  `sunnypilot.ai`. You can turn it back on in settings.

If konik is unreachable at that boot, the device stays unregistered, runs
normally, and retries registration at the next boot.

## Pairing

1. Sign in at `https://stable.konik.ai` (GitHub login).
2. On the device: Settings → Device → Pair Device.
3. Scan the QR code with your phone.

The QR opens `https://stable.konik.ai/?pair={jwt}`, the same flow Comma
Connect uses.

Each device needs its own key pair at `/persist/comma/id_rsa`. A cloned device
must generate a new key pair, or the two devices share one identity.

## What is different from comma

- Comma Connect (app and website) cannot see the device.
- comma prime does not exist. The prime promo is hidden.
- Some API features (for example trips stats) may show no data. konik does not
  implement every comma endpoint. These calls go to `api.konik.ai` and fail
  there; they never reach comma.
- Crash reports stay on the device. The sentry upload to comma's project is
  disabled (`openpilot/system/sentry.py`).
- PC tools work against konik: `API_HOST=https://api.konik.ai ./tools/cabana <route>`.

## Out of scope

AGNOS images and the setup recovery flow still come from comma servers. This
change covers the openpilot software layer only.
