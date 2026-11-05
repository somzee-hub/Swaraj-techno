{
    "name": "Swaraj Technocrafts: Project Planning Engine",
    "version": "19.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "summary": "Multi-level BOM explosion per project, finite-capacity day-wise planning, "
               "outsourcing flags, multi-unit load, plan export for SAP / legacy ERP",
    "description": """
Pre-sales demo for Swaraj Technocrafts Ltd (special purpose wire processing machinery).

* Project (sale order) to multi-level manufacturing orders, driven by the BOM
* Work centre capacity per day from shift calendars, parallel machines and efficiency
* Day-wise finite-capacity plan across all running projects and both units
* Alternate work centre first, then an outsourcing flag when capacity runs out
* Job-work purchase orders created from the outsourcing flags
* Material shortage view and RFQs from the same plan
* Plan export to Excel for SAP or the existing ERP, and write-back to work orders
* Demo data that can be loaded and removed from one screen
""",
    "author": "Ochre Digital",
    "website": "https://ochre.digital",
    "license": "OPL-1",
    "depends": [
        "crm",
        "sale_management",
        "sale_stock",
        "sale_mrp",
        "purchase_stock",
        "mrp",
        "mrp_subcontracting",
        "project",
        "sale_project",
        "project_mrp",
        "maintenance",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/plan_views.xml",
        "views/mrp_views.xml",
        "views/sale_views.xml",
        "wizard/demo_loader_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
}
