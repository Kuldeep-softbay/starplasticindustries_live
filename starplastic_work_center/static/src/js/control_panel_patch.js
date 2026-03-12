/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlPanelButtons } from "@mrp_workorder/mrp_display/control_panel";
import { useService } from "@web/core/utils/hooks";

patch(ControlPanelButtons.prototype, {

    setup(){
        super.setup();
        this.actionService = useService("action");
    },

    onClickShiftHourEntry() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Shift / Hour Entry",
            res_model: "work.center.shift",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    },

});