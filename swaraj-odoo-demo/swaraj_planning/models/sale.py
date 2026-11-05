import math
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    swaraj_mo_ids = fields.One2many("mrp.production", "swaraj_sale_id", string="Production Orders")
    swaraj_mo_count = fields.Integer(compute="_compute_swaraj_mo_count")

    @api.depends("swaraj_mo_ids")
    def _compute_swaraj_mo_count(self):
        for order in self:
            order.swaraj_mo_count = len(order.swaraj_mo_ids)

    def _swaraj_bom_days(self, bom, qty):
        """Rough elapsed days a BOM level needs, used to offset sub-assembly deadlines."""
        hours = sum(op.time_cycle_manual for op in bom.operation_ids) / 60.0 * qty
        return max(1, math.ceil(hours / 16.0))

    def _swaraj_create_mo(self, product, qty, deadline, parent, level, created):
        Bom = self.env["mrp.bom"]
        wh = self.warehouse_id
        bom = Bom._bom_find(product, picking_type=wh.manu_type_id,
                            company_id=self.company_id.id, bom_type="normal").get(product)
        if not bom:
            return
        mo = self.env["mrp.production"].create({
            "product_id": product.id,
            "product_qty": qty,
            "product_uom_id": product.uom_id.id,
            "bom_id": bom.id,
            "picking_type_id": wh.manu_type_id.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "date_deadline": deadline,
            "project_id": self.project_id.id,
            "swaraj_sale_id": self.id,
            "swaraj_parent_mo_id": parent.id if parent else False,
            "swaraj_level": level,
        })
        created.append(mo)
        child_deadline = deadline - timedelta(days=self._swaraj_bom_days(bom, qty) + 1)
        for line in bom.bom_line_ids:
            child_qty = line.product_qty * qty / (bom.product_qty or 1.0)
            self._swaraj_create_mo(line.product_id, child_qty, child_deadline, mo, level + 1, created)

    def action_swaraj_explode(self):
        """MRP explosion: one production order per BOM level, linked to the project."""
        for order in self:
            if order.state != "sale":
                raise UserError(_("Confirm %s before releasing it to production.", order.name))
            if order.swaraj_mo_ids:
                raise UserError(_("%s is already released to production.", order.name))
            if not order.project_id:
                order.project_id = self.env["project.project"].create({
                    "name": "%s - %s" % (order.name, order.partner_id.name),
                    "partner_id": order.partner_id.id,
                    "company_id": order.company_id.id,
                    "allow_billable": True,
                })
            deadline = order.commitment_date or (fields.Datetime.now() + timedelta(days=45))
            created = []
            for line in order.order_line.filtered(lambda l: l.product_id and not l.display_type):
                order._swaraj_create_mo(line.product_id, line.product_uom_qty, deadline,
                                        False, 0, created)
            if not created:
                raise UserError(_("No bill of materials found for the machines on %s.", order.name))
            mos = self.env["mrp.production"].browse([m.id for m in created])
            mos.action_confirm()
        return self.action_swaraj_view_mos()

    def action_swaraj_view_mos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Production Orders"),
            "res_model": "mrp.production",
            "view_mode": "list,form",
            "domain": [("swaraj_sale_id", "=", self.id)],
            "context": {"group_by": "swaraj_level"},
        }
