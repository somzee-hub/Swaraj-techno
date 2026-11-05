from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    swaraj_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Unit",
        help="Plant (unit) where this work centre physically sits.")
    swaraj_parallel_units = fields.Integer(
        string="Machines / Bays", default=1,
        help="Number of identical machines or bays in this work centre. "
             "Daily capacity = shift hours x machines x efficiency.")
    swaraj_outsource_allowed = fields.Boolean(
        string="Can Be Outsourced",
        help="When this work centre is full, the planner may flag the operation for job work.")
    swaraj_jobwork_vendor_id = fields.Many2one("res.partner", string="Job-Work Vendor")
    swaraj_jobwork_lead_days = fields.Integer(string="Job-Work Lead Time (days)", default=4)
    swaraj_jobwork_rate = fields.Float(string="Job-Work Rate per Hour")

    def _swaraj_daily_hours(self, day):
        """Available hours on a date: shift hours x machines x efficiency."""
        self.ensure_one()
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar:
            return 0.0
        weekday = str(day.weekday())
        hours = sum(
            att.duration_hours
            for att in calendar.attendance_ids
            if att.dayofweek == weekday and att.day_period != "lunch"
        )
        # public holidays and closures defined on the calendar
        holiday = calendar.leave_ids.filtered(
            lambda lv: not lv.resource_id
            and lv.date_from.date() <= day <= lv.date_to.date())
        if holiday:
            return 0.0
        eff = (self.time_efficiency or 100.0) / 100.0
        return round(hours * max(self.swaraj_parallel_units, 1) * eff, 2)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    swaraj_sale_id = fields.Many2one("sale.order", string="Customer Order", index=True)
    swaraj_parent_mo_id = fields.Many2one(
        "mrp.production", string="Feeds Into", index=True,
        help="Higher-level order that consumes this sub-assembly.")
    swaraj_child_mo_ids = fields.One2many(
        "mrp.production", "swaraj_parent_mo_id", string="Sub-assembly Orders")
    swaraj_level = fields.Integer(string="BOM Level", default=0)
    swaraj_warehouse_id = fields.Many2one(
        related="picking_type_id.warehouse_id", string="Plant Unit", store=True)
