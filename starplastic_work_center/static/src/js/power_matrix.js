/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";

class PowerMatrix extends Component {

    setup() {

        this.state = useState({
            data: [],
            machines: []
        });

        onWillStart(async () => {

            const response = await fetch("/power/matrix/data", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({}),
            });

            const result = await response.json();

            this.state.data = result.result.rows || [];
            this.state.machines = result.result.workcenters || [];
        });
    }
}

PowerMatrix.template = "starplastic_work_center.power_matrix_template";

registry.category("actions").add(
    "power_consumption_matrix_view",
    PowerMatrix
);