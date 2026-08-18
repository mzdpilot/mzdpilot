# mzdpilot install

mzdpilot is the zoompilot-based fork that carries the Mazda torque
interceptor (TI) support. The code lives in the `mzdpilot` GitHub org:

| Repo | Content |
| --- | --- |
| `mzdpilot/mzdpilot` | the fork itself (this tree) |
| `mzdpilot/opendbc` | car ports, DBCs, safety (TI changes) |
| `mzdpilot/panda` | panda firmware (TI can-mode case) |

The org repo may be renamed to `mzdpilot/openpilot`. GitHub keeps old
URLs working after a rename, so both names reach the same code.

## What to expect

- The TI feature is **off by default**. Enable it only with the device
  installed: Settings → Vehicle → Torque Interceptor (Experimental).
- The `torque-interceptor` branch is source code, not a prebuilt release.
  A device compiles it on first boot, the same way a zoompilot `develop`
  install works.
- Large files (models, fonts, sounds) fetch from the sunnypilot public
  GitLab LFS bucket, as in zoompilot itself.

## Install on a comma device

SSH into the device, then:

```
cd /data
mv openpilot openpilot.bak   # keep the previous install
git clone -b torque-interceptor --recurse-submodules \
  https://github.com/mzdpilot/mzdpilot.git openpilot
cd openpilot
git lfs pull --exclude openpilot/selfdrive/modeld/models/big_driving_supercombo.onnx
mv /data/openpilot.bak/continue.sh /data/ 2>/dev/null || true  # if you kept a custom one
reboot
```

If the clone was made without `--recurse-submodules`:

```
cd /data/openpilot
git submodule update --init opendbc_repo panda
```

First boot compiles the software. Confirm the TI toggle appears under
Settings → Vehicle after the car is fingerprinted (onroad once).

## Wiring reminder for the TI device

The TI1 sits on the comma power RJ45 chain. The panda switches its bus 1
to the OBD-II pins when the toggle is on (see
`docs/torque-interceptor-port.md`). Follow the MoreTorque install guide
for the hardware side.
