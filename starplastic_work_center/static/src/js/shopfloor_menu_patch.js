/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MrpMenuDialog } from "@mrp_workorder/components/dialog/mrp_menu_dialog";

patch(MrpMenuDialog.prototype, {

    setup() {
        super.setup(...arguments);

        // attach handler to component instance
        this.addMachineData = () => {

            const workorder = this.props.record.data;

            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Machine Data",
                res_model: "machine.data",
                views: [[false, "form"]],
                target: "new",

                context: {
                    default_workorder_id: this.props.record.resId,
                    default_production_id: workorder.production_id?.[0],
                    default_workcenter_id: workorder.workcenter_id?.[0],
                    default_product_id: workorder.product_id?.[0],
                },
            });

            this.props.close();
        };
    },

});