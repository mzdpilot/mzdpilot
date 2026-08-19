"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import json
from pathlib import Path

from openpilot.common.basedir import BASEDIR
from openpilot.common.hardware.hw import Paths
from openpilot.common.swaglog import cloudlog
from openpilot.common.utils import run_cmd, run_cmd_default
from openpilot.sunnypilot.selfdrive.car.sync_sunnylink_params import CAR_LIST_JSON_OUT

ONROAD_BRIGHTNESS_MIGRATION_VERSION: str = "1.0"
ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION: str = "1.0"

# index → seconds mapping for OnroadScreenOffTimer (SSoT)
ONROAD_BRIGHTNESS_TIMER_VALUES = {0: 3, 1: 5, 2: 7, 3: 10, 4: 15, 5: 30, **{i: (i - 5) * 60 for i in range(6, 16)}}
VALID_TIMER_VALUES = set(ONROAD_BRIGHTNESS_TIMER_VALUES.values())

ZOOMPILOT_ORIGIN: str = "https://github.com/zoompilot/zoompilot.git"
ZOOMPILOT_BRANCH: str = "main"

# origins we shipped installs from before the zoompilot org existed
LEGACY_ORIGINS: tuple[str, ...] = ("github.com/zephleggett/openpilot",)
# only branches we published; anything else on those forks is someone else's work
LEGACY_BRANCHES: tuple[str, ...] = ("mazda-dev", "zoompilot")


def _migrate_car_platform_bundle(_params):
  bundle = _params.get("CarPlatformBundle")
  if bundle is None:
    return

  old_platform = bundle.get("platform")
  if not old_platform:
    return

  from opendbc.car.fingerprints import MIGRATION  # lazy: avoids heavy import at module level
  if old_platform not in MIGRATION:
    return

  new_platform = str(MIGRATION[old_platform])

  with open(CAR_LIST_JSON_OUT) as f:
    car_list = json.load(f)

  candidates = [(k, v) for k, v in car_list.items() if v.get("platform") == new_platform]
  if candidates:
    old_model = bundle.get("model")
    key, data = next(((k, v) for k, v in candidates if v.get("model") == old_model), candidates[0])
    bundle = {**data, "name": key}
  else:
    bundle["platform"] = new_platform

  _params.put("CarPlatformBundle", bundle, block=True)
  cloudlog.info(f"params_migration: CarPlatformBundle migrated {old_platform!r} -> {new_platform!r}")


def _normalize_origin(url: str) -> str:
  return url.replace("git@", "", 1).replace(".git", "", 1).replace("https://", "", 1).replace(":", "/", 1)


def _migrate_zoompilot_channel(_params):
  """Move devices installed from a personal fork onto zoompilot/zoompilot:main.

  updated.py only ever runs `git fetch origin <branch>` and has no way to repoint a
  remote, so the origin URL is rewritten here. Submodules need no handling: every
  fetch runs `git submodule sync`, which follows the .gitmodules change on the target
  branch over to zoompilot/opendbc on its own.
  """
  origin = run_cmd_default(["git", "config", "--get", "remote.origin.url"], cwd=BASEDIR)
  branch = run_cmd_default(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=BASEDIR)
  if not origin or branch not in LEGACY_BRANCHES:
    return

  if _normalize_origin(origin) in LEGACY_ORIGINS:
    # Writing .git costs one skipped update activation: launch_chffrplus.sh treats a
    # .git newer than .overlay_init as the user switching forks. updated.py rebuilds
    # the overlay and re-touches the canary, so the next boot installs. Only pay that
    # once, by rewriting solely when the URL is still wrong.
    run_cmd(["git", "remote", "set-url", "origin", ZOOMPILOT_ORIGIN], cwd=BASEDIR)
    cloudlog.info(f"params_migration: origin {origin!r} -> {ZOOMPILOT_ORIGIN!r}")

  # UpdaterTargetBranch is CLEAR_ON_MANAGER_START and is wiped just before this runs,
  # so it cannot carry the migration across boots. Re-assert it every boot until the
  # checkout actually lands on ZOOMPILOT_BRANCH, at which point branch leaves
  # LEGACY_BRANCHES and this whole migration goes quiet.
  _params.put("UpdaterTargetBranch", ZOOMPILOT_BRANCH, block=True)
  cloudlog.info(f"params_migration: UpdaterTargetBranch set to {ZOOMPILOT_BRANCH!r} (on {branch!r})")


def _migrate_off_comma_backend(_params):
  """mzdpilot uses konik as its backend and never talks to comma. One-shot:
  turn sunnylink off and drop the comma-issued dongle id so the device
  registers with konik. register() retries on later boots while konik is
  unreachable."""
  if not _params.get_bool("SunnylinkDisabledMigrated"):
    _params.put_bool("SunnylinkEnabled", False, block=True)
    _params.put_bool("SunnylinkDisabledMigrated", True, block=True)
    cloudlog.info("params_migration: sunnylink disabled")

  if not _params.get_bool("KonikRegistrationMigrated"):
    _params.remove("DongleId")
    persist_dongle = Path(Paths.persist_root()) / "comma" / "dongle_id"
    if persist_dongle.is_file():
      persist_dongle.unlink()
    _params.put_bool("KonikRegistrationMigrated", True, block=True)
    cloudlog.info("params_migration: comma dongle id cleared, next registration goes to konik")


def run_migration(_params):
  # migrate OnroadScreenOffBrightness
  if _params.get("OnroadScreenOffBrightnessMigrated") != ONROAD_BRIGHTNESS_MIGRATION_VERSION:
    try:
      val = _params.get("OnroadScreenOffBrightness", return_default=True)
      if val >= 2:  # old: 5%, new: Screen Off
        new_val = val + 1
        _params.put("OnroadScreenOffBrightness", new_val, block=True)
        log_str = f"Successfully migrated OnroadScreenOffBrightness from {val} to {new_val}."
      else:
        log_str = "Migration not required for OnroadScreenOffBrightness."

      _params.put("OnroadScreenOffBrightnessMigrated", ONROAD_BRIGHTNESS_MIGRATION_VERSION, block=True)
      cloudlog.info(log_str + f" Setting OnroadScreenOffBrightnessMigrated to {ONROAD_BRIGHTNESS_MIGRATION_VERSION}")
    except Exception as e:
      cloudlog.exception(f"Error migrating OnroadScreenOffBrightness: {e}")

  # migrate OnroadScreenOffTimer
  if _params.get("OnroadScreenOffTimerMigrated") != ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION:
    try:
      val = _params.get("OnroadScreenOffTimer", return_default=True)
      if val not in VALID_TIMER_VALUES:
        _params.put("OnroadScreenOffTimer", 15, block=True)
        log_str = f"Successfully migrated OnroadScreenOffTimer from {val} to 15 (default)."
      else:
        log_str = "Migration not required for OnroadScreenOffTimer."

      _params.put("OnroadScreenOffTimerMigrated", ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION, block=True)
      cloudlog.info(log_str + f" Setting OnroadScreenOffTimerMigrated to {ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION}")
    except Exception as e:
      cloudlog.exception(f"Error migrating OnroadScreenOffTimer: {e}")

  _migrate_car_platform_bundle(_params)

  try:
    _migrate_zoompilot_channel(_params)
  except Exception as e:
    cloudlog.exception(f"Error migrating to the zoompilot channel: {e}")

  try:
    _migrate_off_comma_backend(_params)
  except Exception as e:
    cloudlog.exception(f"Error migrating off the comma backend: {e}")
