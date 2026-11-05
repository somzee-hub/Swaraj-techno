"""Load / remove Swaraj Technocrafts demo data.

Every record created here is tagged in ir.model.data under the module name
'swaraj_demo', so the whole set can be removed again in reverse order.
Customer and vendor names are illustrative, not real Swaraj accounts.
"""
import logging
from datetime import datetime, time, timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TAG = "swaraj_demo"

# --------------------------------------------------------------------------
# Master data
# --------------------------------------------------------------------------
VENDORS = [
    # key, name, city, role
    ("v_steel", "Indore Steel Traders", "Indore", "supplier"),
    ("v_bearing", "Bharat Bearings Agency", "Indore", "supplier"),
    ("v_drives", "Electro Drives India", "Pune", "supplier"),
    ("v_cast", "Malwa Castings and Forgings", "Dewas", "supplier"),
    ("v_jw_machining", "Pithampur Precision Works (Job Work)", "Pithampur", "jobwork"),
    ("v_jw_fab", "Sanwer Road Fabricators (Job Work)", "Indore", "jobwork"),
    ("v_jw_heat", "Dewas Heat Treatment Services (Job Work)", "Dewas", "jobwork"),
]

CUSTOMERS = [
    ("c_narmada", "Narmada Wires Pvt Ltd", "Jabalpur", "IN"),
    ("c_deccan", "Deccan Steel Wire Ltd", "Hyderabad", "IN"),
    ("c_gulf", "Gulf Wire Industries LLC", "Sharjah", "AE"),
    ("c_shakti", "Shakti Ropes Pvt Ltd", "Raipur", "IN"),
    ("c_vindhya", "Vindhya Galvanisers", "Satna", "IN"),
    ("c_konkan", "Konkan Cable Industries", "Ratnagiri", "IN"),
]

# work centre: key, code, name, unit, machines, calendar, efficiency, outsource, vendor, lead, rate, cost/h, alternatives
WORKCENTERS = [
    ("wc_cnc1", "U1-CNC", "CNC Turning Centre", "u1", 2, "cal_2shift", 90, True, "v_jw_machining", 4, 900, 750, ["wc_cnc2"]),
    ("wc_vmc1", "U1-VMC", "VMC Machining", "u1", 1, "cal_2shift", 90, True, "v_jw_machining", 5, 1100, 950, []),
    ("wc_hbm1", "U1-HBM", "Horizontal Boring", "u1", 1, "cal_2shift", 85, True, "v_jw_machining", 6, 1400, 1200, []),
    ("wc_fab1", "U1-FAB", "Fabrication and Welding", "u1", 3, "cal_gen", 90, True, "v_jw_fab", 5, 450, 400, ["wc_fab2"]),
    ("wc_ind1", "U1-IND", "Induction Hardening", "u1", 1, "cal_gen", 95, True, "v_jw_heat", 3, 800, 650, []),
    ("wc_tc1", "U1-TC", "TC Coating", "u1", 1, "cal_gen", 95, False, False, 0, 0, 900, []),
    ("wc_grd1", "U1-GRD", "Cylindrical Grinding", "u1", 1, "cal_2shift", 90, True, "v_jw_machining", 4, 950, 800, []),
    ("wc_elc1", "U1-ELC", "Electrical Panel Wiring", "u1", 2, "cal_gen", 95, False, False, 0, 0, 450, []),
    ("wc_asm1", "U1-ASM", "Mechanical Assembly", "u1", 4, "cal_gen", 95, False, False, 0, 0, 400, []),
    ("wc_tst1", "U1-TST", "Testing and Trial Run", "u1", 1, "cal_gen", 100, False, False, 0, 0, 500, []),
    ("wc_pnt1", "U1-PNT", "Painting", "u1", 1, "cal_gen", 100, True, "v_jw_fab", 3, 350, 300, []),
    ("wc_cnc2", "U2-CNC", "CNC Turning Centre U2", "u2", 1, "cal_gen", 85, True, "v_jw_machining", 4, 900, 750, ["wc_cnc1"]),
    ("wc_fab2", "U2-FAB", "Fabrication and Welding U2", "u2", 2, "cal_gen", 85, True, "v_jw_fab", 5, 450, 400, ["wc_fab1"]),
    ("wc_asm2", "U2-ASM", "Assembly and Trial U2", "u2", 2, "cal_gen", 90, False, False, 0, 0, 400, []),
]

# raw / bought-out: key, code, name, uom ('Units' or 'kg'), cost, vendor, on hand
MATERIALS = [
    ("m_en8", "RM-EN8-FRG", "EN8 Forging Blank (Capstan)", "Units", 18500, "v_cast", 10),
    ("m_en19", "RM-EN19-BAR", "EN19 Round Bar 90 mm", "kg", 145, "v_steel", 600),
    ("m_ms", "RM-MS-PLATE", "MS Plate IS2062 (assorted)", "kg", 68, "v_steel", 9000),
    ("m_cast_gb", "BO-GB-CAST", "Gearbox Housing Casting", "Units", 24000, "v_cast", 4),
    ("m_gearset", "BO-GEARSET", "Helical Gear Set", "Units", 38000, "v_cast", 3),
    ("m_brg", "BO-BRG-22220", "Spherical Roller Bearing 22220", "Units", 6200, "v_bearing", 40),
    ("m_mtr30", "BO-MTR-30KW", "AC Motor 30 kW IE3", "Units", 98000, "v_drives", 6),
    ("m_mtr7", "BO-MTR-7.5KW", "AC Motor 7.5 kW IE3", "Units", 32000, "v_drives", 2),
    ("m_vfd30", "BO-VFD-30KW", "VFD 30 kW", "Units", 72000, "v_drives", 5),
    ("m_plc", "BO-PLC-HMI", "PLC with 10 inch HMI", "Units", 145000, "v_drives", 1),
    ("m_cable", "BO-CABLE-KIT", "Cable and Wiring Kit", "Units", 42000, "v_drives", 2),
    ("m_diebox", "BO-DIEBOX", "Die Box with Soap Stirrer", "Units", 21000, "v_cast", 8),
    ("m_pump", "BO-PUMP", "Coolant Pump Set", "Units", 26000, "v_drives", 2),
    ("m_paint", "CN-PAINT", "PU Paint and Primer", "kg", 420, "v_steel", 120),
    ("m_fast", "CN-FASTENER", "Fastener Kit", "Units", 8500, "v_steel", 6),
]

# made items: key, code, name, sale price (0 = sub-assembly), operations, components
# operation: (sequence, name, workcenter key, minutes per unit)
MADE = [
    # level 2 parts
    ("p_cd600", "SA-CD-600", "Capstan Drum 600 mm", 0,
     [(10, "Rough and Finish Turning", "wc_cnc1", 210), (20, "Induction Hardening", "wc_ind1", 60),
      (30, "TC Coating", "wc_tc1", 120), (40, "Finish Grinding", "wc_grd1", 90)],
     [("m_en8", 1)]),
    ("p_cd1000", "SA-CD-1000", "Capstan Drum 1000 mm", 0,
     [(10, "Rough and Finish Turning", "wc_cnc1", 420), (20, "Induction Hardening", "wc_ind1", 120),
      (30, "TC Coating", "wc_tc1", 180), (40, "Finish Grinding", "wc_grd1", 150)],
     [("m_en8", 1)]),
    ("p_shaft", "SA-SH-60", "Capstan Main Shaft", 0,
     [(10, "CNC Turning", "wc_cnc1", 120), (20, "Bearing Seat Grinding", "wc_grd1", 60)],
     [("m_en19", 45)]),
    ("p_gb60", "SA-GB-60", "Gearbox Assembly 60", 0,
     [(10, "Housing Machining", "wc_vmc1", 240), (20, "Gearbox Assembly", "wc_asm1", 150)],
     [("m_cast_gb", 1), ("m_gearset", 1), ("m_brg", 2)]),
    ("p_gb100", "SA-GB-100", "Gearbox Assembly 100", 0,
     [(10, "Housing Machining", "wc_vmc1", 420), (20, "Gearbox Assembly", "wc_asm1", 240)],
     [("m_cast_gb", 1), ("m_gearset", 1), ("m_brg", 2)]),
    ("p_cone", "SA-CP-21", "Cone Pulley Assembly (21 die)", 0,
     [(10, "Cone Turning", "wc_cnc1", 540), (20, "TC Coating", "wc_tc1", 240),
      (30, "Profile Grinding", "wc_grd1", 240), (40, "Cone Assembly", "wc_asm1", 240)],
     [("m_en19", 180), ("m_brg", 2)]),
    ("p_cradle", "SA-CR-6", "Cradle Assembly (Planetary)", 0,
     [(10, "Cradle Fabrication", "wc_fab2", 300), (20, "Cradle Machining", "wc_cnc2", 240),
      (30, "Cradle Assembly", "wc_asm2", 180)],
     [("m_ms", 260), ("m_brg", 2)]),
    # level 1 sub-assemblies
    ("p_cba600", "SA-CBA-600", "Capstan Block Assembly 600", 0,
     [(10, "Block Assembly", "wc_asm1", 300), (20, "Run-out Check", "wc_tst1", 45)],
     [("p_cd600", 1), ("p_shaft", 1), ("p_gb60", 1), ("m_mtr30", 1), ("m_brg", 2), ("m_diebox", 1)]),
    ("p_cba1000", "SA-CBA-1000", "Capstan Block Assembly 1000", 0,
     [(10, "Block Assembly", "wc_asm1", 480), (20, "Run-out Check", "wc_tst1", 90)],
     [("p_cd1000", 1), ("p_shaft", 1), ("p_gb100", 1), ("m_mtr30", 1), ("m_brg", 2)]),
    ("p_bf_sl", "SA-BF-SL8", "Base Frame SL-8", 0,
     [(10, "Frame Fabrication", "wc_fab1", 1800), (20, "Line Boring", "wc_hbm1", 600),
      (30, "Primer and Paint", "wc_pnt1", 300)],
     [("m_ms", 3200), ("m_paint", 25)]),
    ("p_bf_ivd", "SA-BF-IVD", "Base Frame IVD", 0,
     [(10, "Frame Fabrication", "wc_fab1", 1200), (20, "Line Boring", "wc_hbm1", 420),
      (30, "Primer and Paint", "wc_pnt1", 240)],
     [("m_ms", 1900), ("m_paint", 15)]),
    ("p_bf_wd", "SA-BF-WD", "Base Frame and Wet Tank WD-21", 0,
     [(10, "Frame and Tank Fabrication", "wc_fab1", 2400), (20, "Line Boring", "wc_hbm1", 540),
      (30, "Primer and Paint", "wc_pnt1", 360)],
     [("m_ms", 3800), ("m_paint", 30)]),
    ("p_bf_psm", "SA-BF-PSM", "Base Frame and Rotor Housing PSM", 0,
     [(10, "Frame Fabrication", "wc_fab2", 2700), (20, "Rotor Bore Machining", "wc_hbm1", 720)],
     [("m_ms", 5200), ("m_paint", 35)]),
    ("p_rotor", "SA-RT-6", "Planetary Rotor Assembly", 0,
     [(10, "Rotor Fabrication", "wc_fab2", 1500), (20, "Rotor Shaft Turning", "wc_cnc2", 720),
      (30, "Rotor Assembly and Balancing", "wc_asm2", 960)],
     [("m_ms", 2100), ("m_brg", 4), ("p_cradle", 6)]),
    ("p_ecp_sl", "SA-ECP-SL8", "Control Panel SL-8 (PLC + 8 VFD)", 0,
     [(10, "Panel Wiring", "wc_elc1", 1440), (20, "Panel Testing", "wc_tst1", 240)],
     [("m_plc", 1), ("m_vfd30", 8), ("m_cable", 1)]),
    ("p_ecp_sm", "SA-ECP-S", "Control Panel Standard (PLC + 2 VFD)", 0,
     [(10, "Panel Wiring", "wc_elc1", 720), (20, "Panel Testing", "wc_tst1", 120)],
     [("m_plc", 1), ("m_vfd30", 2), ("m_cable", 1)]),
    ("p_cool", "SA-CLS", "Cooling System", 0,
     [(10, "Pipe and Tank Fabrication", "wc_fab1", 360), (20, "Cooling Assembly", "wc_asm1", 240)],
     [("m_pump", 1), ("m_ms", 180)]),
    ("p_spool", "SA-SPL-800", "Spooler Take-up 800", 0,
     [(10, "Spooler Fabrication", "wc_fab1", 360), (20, "Traverse Machining", "wc_vmc1", 240),
      (30, "Spooler Assembly", "wc_asm1", 360)],
     [("m_mtr7", 1), ("m_brg", 2), ("m_ms", 420)]),
    # level 0 machines (what the customer buys)
    ("p_sldm8", "M-SLDM-8", "Straight Line Wire Drawing Machine, 8 Block", 18500000,
     [(10, "Final Mechanical Assembly", "wc_asm1", 2400), (20, "Panel Integration", "wc_elc1", 720),
      (30, "Trial Run with Wire", "wc_tst1", 960), (40, "Final Paint and Packing", "wc_pnt1", 600)],
     [("p_cba600", 8), ("p_bf_sl", 1), ("p_ecp_sl", 1), ("p_cool", 1), ("p_spool", 1), ("m_fast", 1)]),
    ("p_ivd", "M-IVD-1000", "Inverted Vertical Drawing Machine IVD-1000", 9500000,
     [(10, "Final Mechanical Assembly", "wc_asm1", 1800), (20, "Panel Integration", "wc_elc1", 480),
      (30, "Trial Run with Wire", "wc_tst1", 720), (40, "Final Paint and Packing", "wc_pnt1", 480)],
     [("p_cba1000", 1), ("p_bf_ivd", 1), ("p_ecp_sm", 1), ("p_cool", 1), ("m_fast", 1)]),
    ("p_wdm21", "M-WDM-21", "Wet Wire Drawing Machine, 21 Die", 14000000,
     [(10, "Final Mechanical Assembly", "wc_asm1", 2160), (20, "Panel Integration", "wc_elc1", 600),
      (30, "Trial Run with Wire", "wc_tst1", 960), (40, "Final Paint and Packing", "wc_pnt1", 600)],
     [("p_cone", 2), ("p_gb100", 1), ("p_bf_wd", 1), ("p_ecp_sm", 1), ("p_spool", 1), ("m_fast", 1)]),
    ("p_psm6", "M-PSM-6", "Planetary Stranding Machine, 6 Bobbin", 26000000,
     [(10, "Final Assembly", "wc_asm2", 2880), (20, "Panel Integration", "wc_elc1", 600),
      (30, "Trial Run and Lay Length Setting", "wc_asm2", 1200)],
     [("p_rotor", 1), ("p_bf_psm", 1), ("p_cba1000", 1), ("p_ecp_sm", 1), ("m_fast", 2)]),
]

# project: key, customer, unit, machine, qty, due in days, released to production?
PROJECTS = [
    ("so_narmada", "c_narmada", "u1", "p_sldm8", 2, 26, True),
    ("so_deccan", "c_deccan", "u1", "p_ivd", 1, 16, True),
    ("so_gulf", "c_gulf", "u1", "p_wdm21", 1, 30, True),
    ("so_shakti", "c_shakti", "u2", "p_psm6", 1, 40, True),
    ("so_vindhya", "c_vindhya", "u1", "p_sldm8", 1, 55, False),
]

MILESTONES = ["Design Freeze and BOM Release", "Long-lead Procurement", "Machining and Fabrication",
              "Assembly", "Trial Run and Customer FAT", "Dispatch", "Installation and Commissioning"]

LEADS = [
    ("Enquiry: 2 x Planetary Stranding lines (Unit 2)", "c_konkan", 52000000, 40),
    ("Enquiry: Electro galvanizing line", "c_vindhya", 38000000, 20),
    ("Enquiry: IVD-1000 with coiler, export", "c_gulf", 11000000, 60),
]


class SwarajDemoLoader(models.TransientModel):
    _name = "swaraj.demo.loader"
    _description = "Swaraj Demo Data"

    loaded = fields.Boolean(compute="_compute_loaded")
    rename_company = fields.Boolean(string="Rename company to Swaraj Technocrafts Ltd", default=True)
    run_plan = fields.Boolean(string="Run a first plan after loading", default=True)

    def _compute_loaded(self):
        has = bool(self.env["ir.model.data"].search_count([("module", "=", TAG)]))
        for rec in self:
            rec.loaded = has

    # ------------------------------------------------------------------
    def _tag(self, key, record):
        self.env["ir.model.data"].create({
            "module": TAG, "name": key, "model": record._name, "res_id": record.id, "noupdate": True,
        })
        return record

    def action_load(self):
        if self.env["ir.model.data"].search_count([("module", "=", TAG)]):
            raise UserError(_("Demo data is already loaded. Remove it first."))
        env = self.env
        company = env.company
        today = fields.Date.context_today(self)
        R = {}

        if self.rename_company:
            env["ir.config_parameter"].sudo().set_param("swaraj_demo.old_company_name", company.name)
            company.write({
                "name": "Swaraj Technocrafts Ltd", "street": "Plot 40, Sector II",
                "city": "Pithampur", "zip": "454775",
                "country_id": env.ref("base.in").id,
            })

        # calendars: two-shift for machines, general shift for bays
        def calendar(key, name, slots):
            cal = env["resource.calendar"].create({
                "name": name, "tz": "Asia/Kolkata", "company_id": company.id,
                "attendance_ids": [(5, 0, 0)] + [
                    (0, 0, {"name": "%s %s" % (d, i), "dayofweek": str(d), "hour_from": f, "hour_to": t,
                            "day_period": p})
                    for d in range(6) for i, (f, t, p) in enumerate(slots)],
            })
            R[key] = self._tag(key, cal)

        calendar("cal_2shift", "Swaraj Two Shift (Mon-Sat, 16 h)",
                 [(6.0, 14.0, "morning"), (14.0, 22.0, "afternoon")])
        calendar("cal_gen", "Swaraj General Shift (Mon-Sat, 8.5 h)",
                 [(9.0, 13.0, "morning"), (13.5, 18.0, "afternoon")])
        # one public holiday inside the horizon to show capacity loss
        hol = today + timedelta(days=(6 - today.weekday()) % 7 + 9)  # a Monday ~2 weeks out
        for key in ("cal_2shift", "cal_gen"):
            self._tag("hol_" + key, env["resource.calendar.leaves"].create({
                "name": "Plant Holiday", "calendar_id": R[key].id, "company_id": company.id,
                "date_from": datetime.combine(hol, time(0, 0)),
                "date_to": datetime.combine(hol, time(23, 59)),
            }))

        # units
        for key, code, name in (("u1", "U1", "Unit 1 - Pithampur"), ("u2", "U2", "Unit 2 - New Plant")):
            wh = env["stock.warehouse"].with_context(active_test=False).search(
                [("code", "=", code), ("company_id", "=", company.id)], limit=1)
            if wh:
                wh.write({"active": True, "name": name})
            else:
                wh = env["stock.warehouse"].create({"name": name, "code": code, "company_id": company.id})
            R[key] = self._tag(key, wh)

        # partners
        india = env.ref("base.in")
        for key, name, city, role in VENDORS:
            R[key] = self._tag(key, env["res.partner"].create({
                "name": name, "city": city, "country_id": india.id, "is_company": True,
                "supplier_rank": 1, "comment": "Job-work vendor" if role == "jobwork" else False,
            }))
        for key, name, city, ctry in CUSTOMERS:
            R[key] = self._tag(key, env["res.partner"].create({
                "name": name, "city": city, "country_id": env.ref("base.%s" % ctry.lower()).id,
                "is_company": True, "customer_rank": 1,
            }))

        # work centres
        for (key, code, name, unit, machines, cal, eff, outs, vendor, lead, rate, cost, _alt) in WORKCENTERS:
            R[key] = self._tag(key, env["mrp.workcenter"].create({
                "name": name, "code": code, "company_id": company.id,
                "resource_calendar_id": R[cal].id, "time_efficiency": eff,
                "costs_hour": cost, "swaraj_warehouse_id": R[unit].id,
                "swaraj_parallel_units": machines, "swaraj_outsource_allowed": outs,
                "swaraj_jobwork_vendor_id": R[vendor].id if vendor else False,
                "swaraj_jobwork_lead_days": lead, "swaraj_jobwork_rate": rate,
            }))
        for (key, *_rest, alts) in WORKCENTERS:
            if alts:
                R[key].alternative_workcenter_ids = [(6, 0, [R[a].id for a in alts])]

        # maintenance equipment on the critical machines
        for wc_key in ("wc_cnc1", "wc_vmc1", "wc_hbm1", "wc_grd1"):
            self._tag("eq_" + wc_key, env["maintenance.equipment"].create({
                "name": R[wc_key].name + " #1", "company_id": company.id,
                "serial_no": R[wc_key].code + "-01", "note": "Preventive maintenance every 90 days",
            }))

        # products
        uom_unit = env.ref("uom.product_uom_unit")
        uom_kg = env.ref("uom.product_uom_kgm")
        categ = self._tag("categ", env["product.category"].create({"name": "Swaraj"}))
        for key, code, name, uom, cost, vendor, onhand in MATERIALS:
            u = uom_kg if uom == "kg" else uom_unit
            R[key] = self._tag(key, env["product.product"].create({
                "name": name, "default_code": code, "type": "consu", "is_storable": True,
                "uom_id": u.id, "standard_price": cost, "categ_id": categ.id,
                "sale_ok": False, "purchase_ok": True,
                "seller_ids": [(0, 0, {"partner_id": R[vendor].id, "price": cost, "delay": 7})],
            }))
        for key, code, name, price, ops, comps in MADE:
            R[key] = self._tag(key, env["product.product"].create({
                "name": name, "default_code": code, "type": "consu", "is_storable": True,
                "uom_id": uom_unit.id, "categ_id": categ.id, "list_price": price,
                "sale_ok": bool(price), "purchase_ok": False,
            }))

        # multi-level BOMs with routings
        for key, code, name, price, ops, comps in MADE:
            self._tag("bom_" + key, env["mrp.bom"].create({
                "product_tmpl_id": R[key].product_tmpl_id.id, "product_qty": 1,
                "code": code, "type": "normal", "company_id": company.id,
                "operation_ids": [(0, 0, {"sequence": s, "name": n, "workcenter_id": R[w].id,
                                          "time_mode": "manual", "time_cycle_manual": m})
                                  for s, n, w, m in ops],
                "bom_line_ids": [(0, 0, {"product_id": R[c].id, "product_qty": q}) for c, q in comps],
            }))

        # opening stock in Unit 1
        quants = env["stock.quant"]
        for key, code, name, uom, cost, vendor, onhand in MATERIALS:
            if onhand:
                quants |= env["stock.quant"].with_context(inventory_mode=True).create({
                    "product_id": R[key].id, "location_id": R["u1"].lot_stock_id.id,
                    "inventory_quantity": onhand,
                })
        quants.action_apply_inventory()

        # customer orders (projects)
        for key, cust, unit, machine, qty, due, release in PROJECTS:
            commit = datetime.combine(today + timedelta(days=due), time(12, 0))
            so = self._tag(key, env["sale.order"].create({
                "partner_id": R[cust].id, "warehouse_id": R[unit].id, "commitment_date": commit,
                "client_order_ref": "PO/%s/%s" % (cust[2:].upper(), today.year),
                "order_line": [(0, 0, {"product_id": R[machine].id, "product_uom_qty": qty,
                                       "price_unit": R[machine].list_price, "tax_ids": [(5, 0, 0)]})],
            }))
            so.action_confirm()
            project = self._tag("prj_" + key, env["project.project"].create({
                "name": "%s - %s" % (so.name, R[cust].name), "partner_id": R[cust].id,
                "company_id": company.id, "allow_billable": True,
            }))
            so.project_id = project
            span = (commit.date() - today).days
            for i, ms in enumerate(MILESTONES):
                self._tag("task_%s_%s" % (key, i), env["project.task"].create({
                    "name": ms, "project_id": project.id,
                    "date_deadline": datetime.combine(
                        today + timedelta(days=int(span * (i + 1) / (len(MILESTONES) - 1))), time(12, 0)),
                }))
            if release:
                so.action_swaraj_explode()
                for i, mo in enumerate(so.swaraj_mo_ids):
                    self._tag("mo_%s_%s" % (key, i), mo)
            for i, pick in enumerate(so.picking_ids):
                self._tag("pick_%s_%s" % (key, i), pick)

        # pipeline for Unit 2
        for i, (name, cust, rev, prob) in enumerate(LEADS):
            self._tag("lead_%s" % i, env["crm.lead"].create({
                "name": name, "partner_id": R[cust].id, "type": "opportunity",
                "expected_revenue": rev, "probability": prob,
            }))

        if self.run_plan:
            run = self._tag("plan_run", env["swaraj.plan.run"].create({"note": "Demo plan, all units, all projects"}))
            run.action_run_plan()
            return {"type": "ir.actions.act_window", "res_model": "swaraj.plan.run",
                    "res_id": run.id, "view_mode": "form", "target": "current"}
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_unload(self):
        env = self.env
        # plans and anything generated from them first
        runs = env["swaraj.plan.run"].search([])
        pos = runs.line_ids.purchase_id | runs.material_ids.purchase_id | env["purchase.order"].search(
            [("origin", "in", runs.mapped("name")), ("state", "in", ("draft", "sent", "cancel"))])
        pos.filtered(lambda p: p.state != "cancel").button_cancel()
        pos.unlink()
        runs.unlink()
        # orders released from demo projects during the demo, tagged or not
        demo_sos = env["sale.order"].browse(env["ir.model.data"].search(
            [("module", "=", TAG), ("model", "=", "sale.order")]).mapped("res_id")).exists()
        mos = demo_sos.swaraj_mo_ids.filtered(lambda m: m.state not in ("done", "cancel"))
        mos.action_cancel()
        demo_sos.swaraj_mo_ids.filtered(lambda m: m.state == "cancel").unlink()
        # clear demo stock so units and items can be archived cleanly
        whs = env["stock.warehouse"].browse(env["ir.model.data"].search(
            [("module", "=", TAG), ("model", "=", "stock.warehouse")]).mapped("res_id")).exists()
        if whs:
            quants = env["stock.quant"].search([
                ("location_id", "child_of", whs.view_location_id.ids), ("quantity", "!=", 0)])
            quants.with_context(inventory_mode=True).write({"inventory_quantity": 0})
            quants.action_apply_inventory()
        imd = env["ir.model.data"].search([("module", "=", TAG)], order="id desc")
        recs = [(d, env[d.model].browse(d.res_id).exists()) for d in imd]
        # cancel transactional documents before deleting
        for _d, rec in recs:
            if not rec:
                continue
            if rec._name == "mrp.production" and rec.state not in ("cancel", "done"):
                rec.action_cancel()
            if rec._name == "stock.picking" and rec.state not in ("cancel", "done"):
                rec.action_cancel()
            if rec._name == "sale.order" and rec.state != "cancel":
                rec.with_context(disable_cancel_warning=True)._action_cancel()
        for d, rec in recs:
            if not rec:
                d.unlink()
                continue
            try:
                with env.cr.savepoint():
                    rec.unlink()
            except Exception as exc:  # stock history keeps some records alive
                _logger.info("Archiving %s %s instead of deleting: %s", rec._name, rec.id, exc)
                if "active" in rec._fields:
                    try:
                        with env.cr.savepoint():
                            rec.active = False
                    except Exception as exc2:
                        _logger.info("Kept %s %s: %s", rec._name, rec.id, exc2)
            d.exists().unlink()
        old = env["ir.config_parameter"].sudo().get_param("swaraj_demo.old_company_name")
        if old:
            env.company.name = old
        return {"type": "ir.actions.client", "tag": "reload"}
