import base64
import io
import math
from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

STATUS = [
    ("in_house", "In-house"),
    ("alternate", "Alternate Work Centre"),
    ("outsource", "Outsource"),
    ("late", "In-house, Late"),
]


class SwarajPlanRun(models.Model):
    _name = "swaraj.plan.run"
    _description = "Production Plan Run"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(default=lambda s: _("New"), readonly=True, copy=False)
    date_start = fields.Date(string="Plan From", required=True, default=fields.Date.context_today)
    horizon_days = fields.Integer(string="Horizon (days)", default=60, required=True)
    warehouse_ids = fields.Many2many("stock.warehouse", string="Units",
                                     help="Leave empty to plan all units together.")
    project_ids = fields.Many2many("project.project", string="Projects",
                                   help="Leave empty to plan every open project.")
    hours_per_day_rule = fields.Float(
        string="Standard Hours / Day", default=8.0,
        help="Used to translate remaining downstream hours into days when back-scheduling.")
    state = fields.Selection([("draft", "Draft"), ("planned", "Planned"), ("applied", "Applied to Work Orders")],
                             default="draft", tracking=True)
    note = fields.Text()
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company, required=True)

    line_ids = fields.One2many("swaraj.plan.line", "run_id", string="Day-wise Plan")
    capacity_ids = fields.One2many("swaraj.plan.capacity", "run_id", string="Capacity")
    mo_summary_ids = fields.One2many("swaraj.plan.mo", "run_id", string="Order Status")
    material_ids = fields.One2many("swaraj.plan.material", "run_id", string="Material")

    # day view
    view_date = fields.Date(string="Show Day", default=fields.Date.context_today)
    day_line_ids = fields.One2many("swaraj.plan.line", compute="_compute_day_view")
    day_capacity_ids = fields.One2many("swaraj.plan.capacity", compute="_compute_day_view")

    # KPIs
    kpi_orders = fields.Integer(string="Production Orders", compute="_compute_kpis")
    kpi_projects = fields.Integer(string="Projects Planned", compute="_compute_kpis")
    kpi_hours = fields.Float(string="Total Load (h)", compute="_compute_kpis")
    kpi_outsource_hours = fields.Float(string="Outsourced (h)", compute="_compute_kpis")
    kpi_outsource_ops = fields.Integer(string="Operations to Outsource", compute="_compute_kpis")
    kpi_late_orders = fields.Integer(string="Orders at Risk", compute="_compute_kpis")
    kpi_full_days = fields.Integer(string="Work-centre Days at Full Load", compute="_compute_kpis")
    kpi_shortages = fields.Integer(string="Short Materials", compute="_compute_kpis")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("swaraj.plan.run") or _("New")
        return super().create(vals_list)

    @api.depends("view_date", "line_ids", "capacity_ids")
    def _compute_day_view(self):
        for run in self:
            day = run.view_date
            run.day_line_ids = run.line_ids.filtered(lambda l: l.date == day)
            run.day_capacity_ids = run.capacity_ids.filtered(lambda c: c.date == day)

    @api.depends("line_ids", "mo_summary_ids", "capacity_ids", "material_ids")
    def _compute_kpis(self):
        for run in self:
            run.kpi_orders = len(run.mo_summary_ids)
            run.kpi_projects = len(run.mo_summary_ids.project_id)
            run.kpi_hours = sum(run.line_ids.mapped("hours"))
            out = run.line_ids.filtered(lambda l: l.status == "outsource")
            run.kpi_outsource_hours = sum(out.mapped("hours"))
            run.kpi_outsource_ops = len(out.workorder_id)
            run.kpi_late_orders = len(run.mo_summary_ids.filtered(lambda m: m.status == "late"))
            run.kpi_full_days = len(run.capacity_ids.filtered(lambda c: c.utilization >= 95 or c.excess_hours))
            run.kpi_shortages = len(run.material_ids.filtered(lambda m: m.shortage > 0))

    # ------------------------------------------------------------------
    # Planning engine
    # ------------------------------------------------------------------
    def _swaraj_productions(self):
        domain = [("state", "in", ("confirmed", "progress", "to_close")),
                  ("company_id", "=", self.company_id.id)]
        if self.warehouse_ids:
            domain.append(("swaraj_warehouse_id", "in", self.warehouse_ids.ids))
        if self.project_ids:
            domain.append(("project_id", "in", self.project_ids.ids))
        return self.env["mrp.production"].search(domain)

    def action_run_plan(self):
        for run in self:
            run._run_plan()
        return True

    def _run_plan(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.capacity_ids.unlink()
        self.mo_summary_ids.unlink()
        self.material_ids.unlink()

        mos = self._swaraj_productions()
        if not mos:
            raise UserError(_("No open production orders match this plan. "
                              "Release a customer order to production first."))
        start = self.date_start
        horizon_end = start + timedelta(days=self.horizon_days * 2)
        hpd = self.hours_per_day_rule or 8.0

        # 1. latest finish dates, top-down (customer date drives sub-assembly dates)
        def ops_of(mo):
            return mo.workorder_ids.filtered(lambda w: w.state not in ("done", "cancel")).sorted(
                lambda w: (w.operation_id.sequence, w.id))

        def remaining_hours(wo):
            return max(wo.duration_expected - wo.duration, 0.0) / 60.0

        latest = {}

        def set_latest(mo, finish):
            latest[mo.id] = finish
            mo_days = math.ceil(sum(remaining_hours(w) for w in ops_of(mo)) / hpd)
            for child in mo.swaraj_child_mo_ids & mos:
                set_latest(child, finish - timedelta(days=mo_days + 1))

        roots = mos.filtered(lambda m: not m.swaraj_parent_mo_id or m.swaraj_parent_mo_id not in mos)
        for mo in roots:
            deadline = (mo.date_deadline or mo.date_start or fields.Datetime.now()).date()
            set_latest(mo, deadline)

        # 2. capacity buckets
        cap_cache = {}

        def capacity(wc, day):
            key = (wc.id, day)
            if key not in cap_cache:
                cap_cache[key] = wc._swaraj_daily_hours(day)
            return cap_cache[key]

        used = defaultdict(float)
        excess = defaultdict(float)
        lines = []
        mo_result = {}

        def simulate(primary, hours, earliest):
            """Fill the earliest days with free capacity; alternates fill the gap."""
            alloc = []
            remaining = hours
            day = earliest
            while remaining > 0.001 and day <= horizon_end:
                for wc in primary | primary.alternative_workcenter_ids:
                    free = capacity(wc, day) - used[(wc.id, day)] - sum(
                        h for d, w, h in alloc if d == day and w == wc)
                    if free > 0.001:
                        take = min(free, remaining)
                        alloc.append((day, wc, take))
                        remaining -= take
                        if remaining <= 0.001:
                            break
                if remaining > 0.001:
                    day += timedelta(days=1)
            return alloc, remaining <= 0.001

        # 3. bottom-up, earliest-due-date first within a level
        ordered = mos.sorted(lambda m: (-m.swaraj_level, latest.get(m.id, horizon_end), m.id))
        finish_of = {}
        for mo in ordered:
            earliest = start
            for child in mo.swaraj_child_mo_ids & mos:
                if child.id in finish_of:
                    earliest = max(earliest, finish_of[child.id] + timedelta(days=1))
            mo_latest = latest.get(mo.id, horizon_end)
            ops = ops_of(mo)
            first_day, last_day, out_ops = None, earliest, 0
            for idx, wo in enumerate(ops):
                hours = remaining_hours(wo)
                if hours <= 0:
                    continue
                downstream = sum(remaining_hours(w) for w in ops[idx + 1:])
                op_latest = mo_latest - timedelta(days=math.ceil(downstream / hpd))
                alloc, ok = simulate(wo.workcenter_id, hours, earliest)
                end = alloc[-1][0] if alloc else earliest
                wc = wo.workcenter_id
                if (not ok or end > op_latest) and wc.swaraj_outsource_allowed:
                    vendor_finish = earliest + timedelta(days=max(wc.swaraj_jobwork_lead_days, 1))
                    excess[(wc.id, earliest)] += hours
                    lines.append({
                        "date": earliest, "workcenter_id": wc.id, "workorder_id": wo.id,
                        "production_id": mo.id, "hours": hours, "status": "outsource",
                        "latest_date": op_latest, "finish_date": vendor_finish,
                        "vendor_id": wc.swaraj_jobwork_vendor_id.id,
                        "reason": _("%(wc)s is full until %(day)s; in-house finish %(end)s is past the "
                                    "required date %(req)s.", wc=wc.name, day=end, end=end, req=op_latest),
                    })
                    first_day = first_day or earliest
                    earliest = vendor_finish
                    last_day = max(last_day, vendor_finish)
                    out_ops += 1
                    continue
                late = end > op_latest or not ok
                for day, used_wc, h in alloc:
                    used[(used_wc.id, day)] += h
                    lines.append({
                        "date": day, "workcenter_id": used_wc.id, "workorder_id": wo.id,
                        "production_id": mo.id, "hours": h,
                        "status": "late" if late else ("alternate" if used_wc != wc else "in_house"),
                        "latest_date": op_latest, "finish_date": end,
                        "reason": _("No outsourcing allowed on %s; order will slip.", wc.name) if late else False,
                    })
                first_day = first_day or (alloc[0][0] if alloc else earliest)
                earliest = end
                last_day = max(last_day, end)
            finish_of[mo.id] = last_day
            mo_result[mo.id] = (first_day or start, last_day, out_ops)

        for vals in lines:
            vals["run_id"] = self.id
        self.env["swaraj.plan.line"].create(lines)

        # 4. capacity table, every work centre in scope, every day of the horizon
        wcs = self.env["mrp.workcenter"].search([("company_id", "in", (False, self.company_id.id))])
        if self.warehouse_ids:
            wcs = wcs.filtered(lambda w: not w.swaraj_warehouse_id or w.swaraj_warehouse_id in self.warehouse_ids)
        cap_vals = []
        last = max([v[1] for v in mo_result.values()] + [start + timedelta(days=self.horizon_days)])
        day = start
        while day <= last:
            for wc in wcs:
                avail = capacity(wc, day)
                if not avail and not excess.get((wc.id, day)):
                    continue
                cap_vals.append({
                    "run_id": self.id, "date": day, "workcenter_id": wc.id,
                    "available_hours": avail, "planned_hours": used.get((wc.id, day), 0.0),
                    "excess_hours": excess.get((wc.id, day), 0.0),
                })
            day += timedelta(days=1)
        self.env["swaraj.plan.capacity"].create(cap_vals)

        # 5. order status
        mo_vals = []
        for mo in mos:
            first, fin, out_ops = mo_result.get(mo.id, (start, start, 0))
            due = latest.get(mo.id, fin)
            mo_vals.append({
                "run_id": self.id, "production_id": mo.id, "planned_start": first,
                "planned_finish": fin, "required_date": due, "outsourced_ops": out_ops,
            })
        self.env["swaraj.plan.mo"].create(mo_vals)

        # 6. material requirement from the same orders
        need = defaultdict(float)
        need_by = {}
        for mo in mos:
            for move in mo.move_raw_ids.filtered(lambda m: m.state not in ("done", "cancel")):
                prod = move.product_id
                if self.env["mrp.bom"]._bom_find(prod, bom_type="normal").get(prod):
                    continue  # made in-house, planned above
                need[prod] += move.product_uom_qty
                day = mo_result.get(mo.id, (start,))[0]
                need_by[prod] = min(need_by.get(prod, day), day)
        self.env["swaraj.plan.material"].create([{
            "run_id": self.id, "product_id": p.id, "required_qty": q,
            "on_hand_qty": p.qty_available, "need_by": need_by[p],
        } for p, q in need.items()])

        self.state = "planned"

    # ------------------------------------------------------------------
    # Actions on the plan
    # ------------------------------------------------------------------
    def action_apply_to_workorders(self):
        """Write the planned dates back to the work orders (Odoo used end to end)."""
        self.ensure_one()
        by_wo = defaultdict(list)
        for line in self.line_ids:
            by_wo[line.workorder_id].append(line)
        for wo, plan in by_wo.items():
            first = min(plan, key=lambda l: l.date)
            last = max(plan, key=lambda l: l.finish_date or l.date)
            begin = datetime.combine(first.date, time(3, 0))  # 08:30 IST
            finish_day = last.finish_date or last.date
            end = datetime.combine(finish_day, time(12, 0))
            if end <= begin:
                end = begin + timedelta(hours=max(sum(l.hours for l in plan), 1))
            wo.with_context(force_date=True).write({"date_start": begin, "date_finished": end})
        self.state = "applied"
        return True

    def action_create_jobwork_po(self):
        self.ensure_one()
        todo = self.line_ids.filtered(lambda l: l.status == "outsource" and not l.purchase_id)
        if not todo:
            raise UserError(_("Nothing flagged for outsourcing, or job-work orders already raised."))
        product = self.env["product.product"].search([("default_code", "=", "JOBWORK")], limit=1)
        if not product:
            product = self.env["product.product"].create({
                "name": "Job Work (Machining / Fabrication)", "default_code": "JOBWORK",
                "type": "service", "purchase_ok": True, "sale_ok": False,
            })
        pos = self.env["purchase.order"]
        for vendor in todo.mapped("vendor_id"):
            vlines = todo.filtered(lambda l: l.vendor_id == vendor)
            po = self.env["purchase.order"].create({
                "partner_id": vendor.id,
                "origin": self.name,
                "order_line": [(0, 0, {
                    "product_id": product.id,
                    "name": "%s | %s | %s | %s" % (l.operation_name, l.product_id.display_name,
                                                   l.production_id.name, l.project_id.name or ""),
                    "product_qty": round(l.hours, 2),
                    "product_uom_id": product.uom_id.id,
                    "price_unit": l.workcenter_id.swaraj_jobwork_rate or l.workcenter_id.costs_hour,
                    "date_planned": datetime.combine(l.finish_date or l.date, time(6, 0)),
                }) for l in vlines],
            })
            vlines.write({"purchase_id": po.id})
            pos |= po
        return {
            "type": "ir.actions.act_window", "name": _("Job-Work Orders"),
            "res_model": "purchase.order", "view_mode": "list,form",
            "domain": [("id", "in", pos.ids)],
        }

    def action_create_rfqs(self):
        self.ensure_one()
        short = self.material_ids.filtered(lambda m: m.shortage > 0 and not m.purchase_id)
        if not short:
            raise UserError(_("No open shortages."))
        pos = self.env["purchase.order"]
        groups = defaultdict(lambda: self.env["swaraj.plan.material"])
        for m in short:
            vendor = m.product_id.seller_ids[:1].partner_id
            if not vendor:
                continue
            groups[vendor] |= m
        for vendor, mats in groups.items():
            po = self.env["purchase.order"].create({
                "partner_id": vendor.id, "origin": self.name,
                "order_line": [(0, 0, {
                    "product_id": m.product_id.id, "product_qty": m.shortage,
                    "product_uom_id": m.product_id.uom_id.id,
                    "date_planned": datetime.combine(m.need_by or self.date_start, time(6, 0)),
                }) for m in mats],
            })
            mats.write({"purchase_id": po.id})
            pos |= po
        return {
            "type": "ir.actions.act_window", "name": _("RFQs"),
            "res_model": "purchase.order", "view_mode": "list,form",
            "domain": [("id", "in", pos.ids)],
        }

    def action_export_xlsx(self):
        """Plan export in a flat layout that SAP or the existing ERP can import."""
        self.ensure_one()
        import xlsxwriter
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        head = wb.add_format({"bold": True, "font_name": "Arial", "bottom": 1})
        body = wb.add_format({"font_name": "Arial"})
        datef = wb.add_format({"font_name": "Arial", "num_format": "dd-mmm-yyyy"})

        def sheet(title, headers, rows, date_cols=()):
            ws = wb.add_worksheet(title)
            for c, h in enumerate(headers):
                ws.write(0, c, h, head)
                ws.set_column(c, c, max(12, len(h) + 4))
            for r, row in enumerate(rows, start=1):
                for c, val in enumerate(row):
                    if c in date_cols and val:
                        ws.write_datetime(r, c, datetime.combine(val, time()), datef)
                    else:
                        ws.write(r, c, val if val not in (None, False) else "", body)
            ws.freeze_panes(1, 0)

        sheet("Day Plan",
              ["PlanDate", "Unit", "WorkCentreCode", "WorkCentre", "Project", "CustomerOrder",
               "ProductionOrder", "BOMLevel", "PartCode", "Part", "Operation", "PlannedHours",
               "Decision", "RequiredBy", "PlannedFinish", "JobWorkVendor"],
              [(l.date, l.warehouse_id.name, l.workcenter_id.code, l.workcenter_id.name,
                l.project_id.name, l.production_id.swaraj_sale_id.name, l.production_id.name,
                l.production_id.swaraj_level, l.product_id.default_code, l.product_id.name,
                l.operation_name, round(l.hours, 2), dict(STATUS)[l.status], l.latest_date,
                l.finish_date, l.vendor_id.name)
               for l in self.line_ids.sorted(lambda l: (l.date, l.workcenter_id.code or ""))],
              date_cols=(0, 13, 14))
        sheet("Capacity",
              ["Date", "Unit", "WorkCentreCode", "WorkCentre", "AvailableHours", "PlannedHours",
               "UtilisationPct", "DemandBeyondCapacity"],
              [(c.date, c.warehouse_id.name, c.workcenter_id.code, c.workcenter_id.name,
                c.available_hours, round(c.planned_hours, 2), round(c.utilization, 1),
                round(c.excess_hours, 2)) for c in self.capacity_ids], date_cols=(0,))
        sheet("Order Status",
              ["ProductionOrder", "Project", "Part", "BOMLevel", "PlannedStart", "PlannedFinish",
               "RequiredBy", "DelayDays", "OutsourcedOps", "Status"],
              [(m.production_id.name, m.project_id.name, m.product_id.display_name, m.level,
                m.planned_start, m.planned_finish, m.required_date, m.delay_days,
                m.outsourced_ops, dict(m._fields["status"].selection)[m.status])
               for m in self.mo_summary_ids], date_cols=(4, 5, 6))
        sheet("Material",
              ["PartCode", "Part", "Required", "OnHand", "Shortage", "NeedBy"],
              [(m.product_id.default_code, m.product_id.name, m.required_qty, m.on_hand_qty,
                m.shortage, m.need_by) for m in self.material_ids], date_cols=(5,))
        wb.close()
        att = self.env["ir.attachment"].create({
            "name": "%s.xlsx" % self.name.replace("/", "-"),
            "datas": base64.b64encode(buf.getvalue()),
            "res_model": self._name, "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {"type": "ir.actions.act_url", "url": "/web/content/%s?download=true" % att.id,
                "target": "self"}

    def _open(self, model, name, view_mode, context=None):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": name, "res_model": model,
                "view_mode": view_mode, "domain": [("run_id", "=", self.id)],
                "context": context or {}}

    def action_open_board(self):
        return self._open("swaraj.plan.line", _("Day-wise Plan"), "list,calendar,pivot",
                          {"search_default_group_date": 1, "search_default_group_wc": 1})

    def action_open_capacity(self):
        return self._open("swaraj.plan.capacity", _("Capacity Load"), "pivot,graph,list")

    def action_open_outsource(self):
        return self._open("swaraj.plan.line", _("Outsourcing Flags"), "list",
                          {"search_default_filter_outsource": 1})


class SwarajPlanLine(models.Model):
    _name = "swaraj.plan.line"
    _description = "Day-wise Plan Line"
    _order = "date, workcenter_id, id"

    run_id = fields.Many2one("swaraj.plan.run", required=True, ondelete="cascade", index=True)
    date = fields.Date(required=True, index=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Centre", required=True)
    warehouse_id = fields.Many2one(related="workcenter_id.swaraj_warehouse_id", string="Plant Unit", store=True)
    workorder_id = fields.Many2one("mrp.workorder", string="Work Order", ondelete="cascade")
    operation_name = fields.Char(related="workorder_id.name", string="Operation", store=True)
    production_id = fields.Many2one("mrp.production", string="Production Order", ondelete="cascade")
    product_id = fields.Many2one(related="production_id.product_id", string="Part", store=True)
    project_id = fields.Many2one(related="production_id.project_id", string="Project", store=True)
    level = fields.Integer(related="production_id.swaraj_level", string="Level", store=True)
    hours = fields.Float(string="Hours")
    status = fields.Selection(STATUS, string="Decision", required=True)
    latest_date = fields.Date(string="Required By")
    finish_date = fields.Date(string="Op Finish")
    vendor_id = fields.Many2one("res.partner", string="Job-Work Vendor")
    purchase_id = fields.Many2one("purchase.order", string="Job-Work PO")
    reason = fields.Char()


class SwarajPlanCapacity(models.Model):
    _name = "swaraj.plan.capacity"
    _description = "Work Centre Capacity by Day"
    _order = "date, workcenter_id"

    run_id = fields.Many2one("swaraj.plan.run", required=True, ondelete="cascade", index=True)
    date = fields.Date(required=True, index=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Centre", required=True)
    warehouse_id = fields.Many2one(related="workcenter_id.swaraj_warehouse_id", string="Plant Unit", store=True)
    available_hours = fields.Float(string="Available (h)", aggregator="sum")
    planned_hours = fields.Float(string="Planned (h)", aggregator="sum")
    free_hours = fields.Float(string="Free (h)", compute="_compute_util", store=True, aggregator="sum")
    excess_hours = fields.Float(string="Demand Beyond Capacity (h)", aggregator="sum")
    utilization = fields.Float(string="Utilisation %", compute="_compute_util", store=True, aggregator="avg")

    @api.depends("available_hours", "planned_hours")
    def _compute_util(self):
        for rec in self:
            rec.free_hours = max(rec.available_hours - rec.planned_hours, 0.0)
            rec.utilization = (rec.planned_hours / rec.available_hours * 100.0) if rec.available_hours else 0.0


class SwarajPlanMo(models.Model):
    _name = "swaraj.plan.mo"
    _description = "Planned Order Status"
    _order = "status desc, delay_days desc, required_date"

    run_id = fields.Many2one("swaraj.plan.run", required=True, ondelete="cascade", index=True)
    production_id = fields.Many2one("mrp.production", string="Production Order", required=True, ondelete="cascade")
    project_id = fields.Many2one(related="production_id.project_id", string="Project", store=True)
    product_id = fields.Many2one(related="production_id.product_id", string="Part", store=True)
    level = fields.Integer(related="production_id.swaraj_level", string="Level", store=True)
    warehouse_id = fields.Many2one(related="production_id.swaraj_warehouse_id", string="Plant Unit", store=True)
    planned_start = fields.Date()
    planned_finish = fields.Date()
    required_date = fields.Date(string="Required By")
    outsourced_ops = fields.Integer(string="Outsourced Ops")
    delay_days = fields.Integer(compute="_compute_status", store=True, string="Delay (days)")
    status = fields.Selection([("on_time", "On Time"), ("late", "At Risk")],
                              compute="_compute_status", store=True)

    @api.depends("planned_finish", "required_date")
    def _compute_status(self):
        for rec in self:
            delay = (rec.planned_finish - rec.required_date).days if rec.planned_finish and rec.required_date else 0
            rec.delay_days = max(delay, 0)
            rec.status = "late" if delay > 0 else "on_time"


class SwarajPlanMaterial(models.Model):
    _name = "swaraj.plan.material"
    _description = "Planned Material Requirement"
    _order = "shortage desc"

    run_id = fields.Many2one("swaraj.plan.run", required=True, ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", string="Material", required=True)
    vendor_id = fields.Many2one("res.partner", compute="_compute_vendor", string="Vendor")
    required_qty = fields.Float(string="Required")
    on_hand_qty = fields.Float(string="On Hand")
    shortage = fields.Float(compute="_compute_shortage", store=True)
    need_by = fields.Date(string="Need By")
    purchase_id = fields.Many2one("purchase.order", string="RFQ")

    @api.depends("required_qty", "on_hand_qty")
    def _compute_shortage(self):
        for rec in self:
            rec.shortage = max(rec.required_qty - rec.on_hand_qty, 0.0)

    def _compute_vendor(self):
        for rec in self:
            rec.vendor_id = rec.product_id.seller_ids[:1].partner_id
