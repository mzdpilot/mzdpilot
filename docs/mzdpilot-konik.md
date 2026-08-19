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

## Switching forks

Drives wait on the device until they are uploaded. If konik is unreachable,
drives are not uploaded. They stay in `/data/media/0/realdata` with no
"uploaded" mark. When konik is reachable again, mzdpilot uploads them.

Other openpilot software scans the same folder. It uploads every file without
the mark to its own backend. Software with the comma backend sends those files
to Comma Connect. This includes drives that mzdpilot recorded.

So, before you install other openpilot software on a device that runs mzdpilot:

1. Use Settings → Software → Uninstall, or
2. fully re-flash the device at [flash.comma.ai](https://flash.comma.ai).

Never clone a different fork over the old one by SSH. That method keeps the
drives and the params. The new software can then upload every drive mzdpilot
never uploaded.

What wipes the drives:

- Settings → Software → Uninstall: yes. It erases all of `/data` and formats
  the data partition again. Params, SSH keys, and calibration are erased too.
- Full re-flash at flash.comma.ai: yes. It erases every partition except
  `persist`.

What does not wipe the drives:

- AGNOS updates and AGNOS system-only re-flashes: no. They do not touch
  `/data`.
- SSH clone-over of another fork: no. `/data/media/0/realdata` and
  `/data/params` stay in place.

Sell or give the device away? Uninstall first.

Drives that were already on the device when you installed mzdpilot stay there.
Any drive the old software never uploaded will upload to konik.

## Out of scope

AGNOS images and the setup recovery flow still come from comma servers. This
change covers the openpilot software layer only.
