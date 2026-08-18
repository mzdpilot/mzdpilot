"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.sunnypilot.widgets.list_view import toggle_item_sp


TI_DESCRIPTION = tr_noop(
  'Enable only with the MoreTorque torque interceptor installed and wired per its install guide. '
  'Steering is then assisted by the device down to a stop. This is an experimental feature. Use at your own risk.'
)


class MazdaSettings(BrandSettings):
  def __init__(self):
    super().__init__()

    self.torque_interceptor = toggle_item_sp(
      lambda: tr("Torque Interceptor (Experimental)"),
      description=lambda: tr(TI_DESCRIPTION),
      initial_state=ui_state.params.get_bool("TorqueInterceptorEnabled"),
      callback=self._on_enable_torque_interceptor,
      enabled=lambda: not ui_state.engaged,
    )

    self.items = [
      self.torque_interceptor,
    ]

  def _on_enable_torque_interceptor(self, state: bool):
    if state:
      def confirm_callback(result: int):
        if result == DialogResult.CONFIRM:
          ui_state.params.put_bool("TorqueInterceptorEnabled", True)
          ui_state.params.put_bool("OnroadCycleRequested", True)
        else:
          self.torque_interceptor.action_item.set_state(False)

      content = (f"<h1>{self.torque_interceptor.title}</h1><br>" +
                 f"<p>{self.torque_interceptor.description}</p>")

      dlg = ConfirmDialog(content, tr("Enable"), rich=True, callback=confirm_callback)
      gui_app.push_widget(dlg)
    else:
      ui_state.params.put_bool("TorqueInterceptorEnabled", False)
      ui_state.params.put_bool("OnroadCycleRequested", True)

  def update_settings(self):
    pass
