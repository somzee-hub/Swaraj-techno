{
    "name": "Swaraj Technocrafts: Enterprise App Bundle",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "One-click install of the Odoo 19 Enterprise apps shown in the Swaraj demo",
    "description": """
Install on Odoo.sh (Enterprise) after swaraj_planning. Adds:
Accounting, MRP shop floor, Master Production Schedule, PLM (engineering change orders),
Quality, Maintenance on work centres, Planning, Approvals, Documents and Sign.
""",
    "author": "Ochre Digital",
    "website": "https://ochre.digital",
    "license": "OPL-1",
    "depends": [
        "swaraj_planning",
        "account_accountant",
        "mrp_workorder",
        "mrp_mps",
        "mrp_plm",
        "quality_control",
        "mrp_maintenance",
        "planning",
        "approvals",
        "documents",
        "sign",
    ],
    "data": [],
    "installable": True,
    "application": False,
}
