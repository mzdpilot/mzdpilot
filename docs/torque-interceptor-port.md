# Torque interceptor (TI) port — reconciliation note

Stage A: MoreTorque Torque Interceptor 1 (TI1) on GEN1 Mazdas, ported from
MoreTore/openpilot. Sources: branches `StarPilot-testing` and `release-mici`
(structure; 2026-era layout matches zoompilot) and `mazda-frogpilot`
(April 2026 behavior fixes only). RI (radar interceptor), BlendedACC, and
standstill-hold extras are excluded; alpha-long stays the longitudinal route.

## Protocol (identical in all three MoreTore branches — verified byte-exact)

CAM_LKAS2 (0x249, bus 1, TX to device), DBC `BO_ 585`:
- LKAS_REQUEST 12-bit @bit3, offset -2048 (raw = torque + 2048)
- CHKSUM 12-bit @bit19, offset -2048 — written as the same value as torque
- KEY 32-bit @bit39 = 3294744160 (auth magic)

TI_FEEDBACK (0x24A, bus 1, 50 Hz, RX from device), DBC `BO_ 586`:
- TI_TORQUE_SENSOR 8-bit @bit7, offset -127, range -85..85 (driver torque)
- CHKSUM 8-bit @bit15, offset -127
- VERSION_NUMBER 8-bit @bit23
- STATE 8-bit @bit31 (TI_STATE: DISCOVER=0, OFF=1, DRIVER_OVER=2, RUN=3)
- VIOL 8-bit @bit39, ERROR 8-bit @bit47 (0 = none)
- RAMP_DOWN 8-bit @bit55 (honored only when VERSION_NUMBER > 1)

Checksums are plain DBC signals written by the builder; no C++ can-lib
checksum support needed (matches the existing CAM_LKAS builder style).

## Decisions

1. **TI torque scale and limiter**: frogpilot April design. Separate
   `apply_ti_steer_torque_limits` with independent `ti_apply_last` state and
   TI constants (TI_STEER_MAX 600, DELTA_UP 6, DELTA_DOWN 15, ALLOWANCE 15,
   MULTIPLIER 40, FACTOR 1). StarPilot-testing reuses the stock limiter with
   shared last-torque state (it even stores `ti_apply_torque_last` but passes
   `apply_torque_last` into the limiter) — rejected.
2. **Send gating**: TI frame sent only while `CS.ti_lkas_allowed`
   (STATE == RUN and not RAMP_DOWN). Both CAM_LKAS (stock path, unchanged)
   and CAM_LKAS2 are sent in TI mode, matching MoreTore.
3. **Safety bit**: `MAZDA_PARAM_TORQUE_INTERCEPTOR 8` (MoreTore numbering).
   Bit 1 stays LONG (MoreTore's GEN1=1 conflicts with it; we do not carry a
   GEN1 bit — every zoompilot Mazda is GEN1 in Stage A).
4. **Safety structure**: 4 combos (stock / TI / LONG / TI+LONG) for both TX
   tables and RX checks. TI adds `{0x249, bus 1}` to TX and
   `{0x24A, bus 1, 50 Hz}` to RX checks. Stock 0x240 check stays in all
   combos (EPS still broadcasts it; `steeringTorqueEps` reads it).
   The TI frame is allowlisted without panda torque checks, as in MoreTore:
   the device enforces its own redundant limits (absolute cap, rate limit,
   driver-torque proportional — per MoreTorque docs). The stock CAM_LKAS
   check against MAZDA_STEERING_LIMITS stays untouched.
5. **Forwarding**: modern safety API forwards only bus 0 <-> bus 2, and
   check_relay already blocks the camera's LKAS/HUD from reaching the car,
   so the frogpilot fwd hook is mostly superseded. We add a minimal
   `mazda_fwd_hook` that blocks only 0x249 (defense in depth; frogpilot
   intent preserved, no other forwarding behavior changes).
6. **rx hook driver torque**: with TI, `torque_driver` samples come from
   0x24A on bus 1 (`data[0] - 127`); the 0x240 handler is skipped
   (`&& !torque_interceptor`). All cruise/controls logic unchanged.
7. **CarState**: third CAN parser on bus 1 (`Bus.body`, zoompilot's enum
   already has it) with TI_FEEDBACK, registered only when the TI flag is set.
   With TI: `steeringTorque` from TI_TORQUE_SENSOR, `steeringPressed`
   threshold 6 (TI_STEER_THRESHOLD), camera LKAS faults
   (steerFaultPermanent, invalid LKAS setting) suppressed, steer lockout
   warning gated on `not ti_lkas_allowed`.
8. **Interface**: read `TorqueInterceptorEnabled` param at fingerprint time
   (house pattern: Toyota `_initialize_*` reads Params directly); set
   `CP.flags |= TORQUE_INTERCEPTOR`, `safetyParam |= 8`, force
   `minSteerSpeed = 0` and `steerAtStandstill = True` (independent of the
   EPS steer-to-zero FW gate — the TI removes the EPS speed lockout).
9. **Panda main.c**: add a `SAFETY_MAZDA` case mirroring the default case,
   but with `set_can_mode(CAN_MODE_OBD_CAN2)` when the TI bit (8) is set —
   this maps bus 1 to the OBD-II pins where the TI device sits on the comma
   power RJ45 chain. The default case already sets the intercept relay for
   all car modes, so no relay change is needed.
10. **Ignition**: MoreTore's 0x274 ignition detection serves GEN2/2019+
    cars. Stage A is GEN1-only; not ported. Revisit in Stage B together with
    the `can-ignition-priority` work.
11. **Default OFF**: `TorqueInterceptorEnabled` defaults unset (OFF).
    MoreTore defaults it ON because their distribution assumes the hardware;
    zoompilot must not.
12. **API adaptation**: MoreTore's `self.ccp` field access becomes zoompilot's
    `self.params`; `actuators.torque` API already matches zoompilot.
    StarPilot's `update_steering_pressed` debounce is kept (zoompilot style)
    with the TI threshold.

## Excluded (with reasons)

- RI safety tables, RI carcontroller/radar paths (zoompilot has alpha-long;
  the two systems would fight over CRZ_INFO/CRZ_CTRL and the radar bus).
- BlendedACC filter, standstill hold/resume timers (zoompilot's plan-driven
  `StandstillHold` owns this domain).
- GEN2/GEN3 platforms, `mazda_2019.dbc`, `mazda_2023.dbc`, new fingerprints,
  `update_gen2` carstate, ACC 0x220 — Stage B.
- NoFSC / NoMRCC / ManualTransmission toggles — Stage B scope questions.
- konik.ai redirects, updater/stats changes, starpilot features, PC-build
  hacks — MoreTore infra, not zoompilot's.

## As-built addendum (Stage A)

- The toggle is wired at fingerprint time through the sunnypilot car-params flow
  (`initialize_params` key list -> `_initialize_torque_interceptor` in
  `opendbc/sunnypilot/car/interfaces.py`), before the CAN parsers are built, so
  the TI body parser registers on the same pass.
- The hook also clears `dashcamOnly` (a GEN1 car with TI is controllable) and
  the stock-path steering tune stays on the car's own branch
  (`CarControllerParams` excludes the TI flag from the steer-to-zero EPS gate).
- The toggle UI is `brands/mazda.py` (confirm dialog on enable, onroad cycle on
  change). Param key `TorqueInterceptorEnabled`, default OFF.

## Stage B addendum (TI2 / GEN2 / GEN3, as-built)

- Safety param bit map (final): LONG=1, GEN2=2, GEN3=4, TORQUE_INTERCEPTOR=8,
  GEN1=16. MoreTore's GEN1=1 collided with zoompilot LONG, so GEN1 moved to 16;
  panda main.c gates CAN_MODE_OBD_CAN2 on GEN1 && TI (TI2 uses the aux bus as-is).
- New platforms: CX-8 (GEN1), Mazda 3 2019-24 / CX-30 / CX-50 (GEN2), Mazda 3
  2024-26 / CX-30 23-26 (GEN3). MAZDA_3_2023 ships with no fingerprint data yet
  (MoreTore has none either); CX_30_2023 matches by CAN fingerprint.
- GEN2 longitudinal comes from the TI2 device (ACC 0x220 echo-modify, 50 Hz, with
  the electric-brake hold/resume frame counters). MoreTore enables it
  unconditionally; zoompilot gates the whole TI2 stack behind the same
  TorqueInterceptorEnabled toggle — without it a GEN2/GEN3 car stays dashcam-only.
- GEN3 is steering-only (MoreTore parity: no longitudinal there yet).
- Checksums: mazda_2019/mazda_2023 prefixes wired in can/dbc.py
  (MAZDA2019_CHECKSUM, additive with per-address seeds 0x2a/0x53). The python
  parser/packer needs no C++ changes. mazda_2017 is deliberately NOT wired — its
  signals are named CHKSM and stock behavior stays bit-identical.
- Deviations from StarPilot-testing, on purpose: the fwd hook blocks 0x249 on
  every bus (SP has no gen2/3 fwd hook); cancel/resume buttons, HUD alerts, ICBM,
  and alpha-long are GEN1-gated; GEN2 reports the ACC wire value through
  actuatorsOutput.accel; BlendedACC and the CEStatus filter stay excluded.
- Known follow-up: the GEN2 ACC frame is allowlisted without a panda-side accel
  range check (SP parity; stock-echo frames must pass unchanged). Revisit with
  hardware. centerToFront stays at the zoompilot-global 0.41 where MoreTore used
  0.38 on some GEN2 platforms.
