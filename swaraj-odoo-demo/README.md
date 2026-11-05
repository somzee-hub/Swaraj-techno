# Swaraj Technocrafts: Odoo 19 Demo

Pre-sales demo for Swaraj Technocrafts Ltd, Pithampur (special purpose wire processing machinery: wire drawing, wire rope, surface treatment lines). Built for a buyer who has run an implementation before and is comparing Odoo with SAP. Keep it short and on planning.

## What is in this repo

| Module | Runs on | Purpose |
|---|---|---|
| `swaraj_planning` | Community and Enterprise | Project to multi-level MRP, finite-capacity day-wise plan, outsourcing flags, job-work POs, material shortages, plan export, demo data loader |
| `swaraj_enterprise_apps` | Enterprise (Odoo.sh) only | One-click install of Accounting, MRP shop floor, MPS, PLM, Quality, Maintenance, Planning, Approvals, Documents, Sign |

`swaraj_planning` was installed and tested end to end on a clean Odoo 19 database: install, load demo data, run plan, raise job-work POs and RFQs, export, write back to work orders, remove demo data, reload. `swaraj_enterprise_apps` is a dependency list only; it could not be tested here because Enterprise source is not available outside Odoo.sh. If Odoo.sh rejects a module name, delete that line from its manifest.

## Setup on Odoo.sh

1. Push this repo to a branch of the Odoo.sh project (same flow as the Creative Fabtech demo).
2. Install **Swaraj Technocrafts: Project Planning Engine** from Apps. On a fresh build use `-i swaraj_planning`, not `-u`.
3. Install **Swaraj Technocrafts: Enterprise App Bundle**.
4. Manufacturing > Project Planning > Demo Data > Load Demo Data. Takes about 10 seconds and opens the first plan.
5. After the meeting, the same screen removes everything. Records with stock history are archived, not deleted.

All dates are relative to the day you load, so the demo is always current. Customer and vendor names are illustrative, not Swaraj accounts.

## What the demo data contains

- Two units: Unit 1 Pithampur and Unit 2 New Plant, one company, one database.
- 14 work centres with machine counts, shift calendars (two-shift for CNC, VMC, boring, grinding; general shift for bays), efficiency, a plant holiday, alternates across units, job-work vendors and lead times.
- Four machine families with three-level BOMs and routings: Straight Line 8-Block, IVD-1000, Wet Drawing 21-Die, Planetary Stranding 6-Bobbin. Sub-assemblies are shared (capstan blocks, gearboxes, panels, spoolers), as in a real SPM shop.
- Five customer projects of Rs 0.95 to 3.7 crore each. Four are released to production (32 production orders, 86 work orders); one is kept back to release live.
- Project milestones from design freeze to commissioning, maintenance equipment on the critical machines, and three Unit 2 enquiries in CRM.

On a fresh load the first plan shows: about 1,519 hours of load across 4 projects, 10 operations flagged for outsourcing (about 350 hours), 58 work-centre days at full load, 14 short materials, and the Narmada 2 x SL-8 order at risk by about 6 days because testing and assembly bays cannot be outsourced. That is the story to tell.

## Demo flow, 25 minutes, mapped to his seven points

| # | His requirement | Show | Where |
|---|---|---|---|
| 1 | BOM per machine with levels | Open M-SLDM-8 BOM. Expand capstan block to drum and shaft. Show operations and work centres on each level | Manufacturing > Products > Bills of Materials |
| 2 | MRP runs off the BOM | Open the held-back Vindhya order and press **Release to Production (MRP)**. Nine orders appear, one per BOM level, linked to the project and dated back from the customer date | Sales > Orders |
| 3 | Machine capacity and utilisation | Open a work centre: machines, shift calendar, efficiency, alternate, outsourcing setup. Then Capacity Load pivot: work centre by day, utilisation, demand beyond capacity | Project Planning > Capacity Load |
| 4 | Day-wise planning | Plan run > **What Can We Build On...** tab. Pick any date: free hours per work centre and every job planned that day | Project Planning > Plan Runs |
| 5 | Outsourcing decision | Outsourcing Flags list: the operation, why it was flagged, required date, vendor. Press **Raise Job-Work POs** | Project Planning > Outsourcing Flags |
| 6 | Many projects at once | Project Status grouped by project: start, finish, required date, delay. Point to the Narmada risk and the alternates used across Unit 1 and Unit 2 | Project Planning > Project Status |
| 7 | Plan back to the main ERP | **Export Plan (Excel)**: Day Plan, Capacity, Order Status, Material. Flat columns built for an SAP or legacy ERP import. Then **Apply to Work Orders** to show the Odoo-only path | Plan run header |

Close on reporting: the same data in pivot and graph views, grouped by unit, project, work centre or week, exportable without IT. On Enterprise, add the work order Gantt and the Master Production Schedule as the standard Odoo views on top.

## How the planner decides

1. Customer date sets the latest finish of the machine. Each sub-assembly gets a latest finish earlier by the time its parent needs.
2. Orders are planned bottom up, deepest level first, earliest due date first, across all projects together.
3. Each operation takes the earliest day with free hours on its work centre. If it is full, the alternate work centre is tried the same day.
4. If the operation would still finish after its required date and the work centre allows job work, it is flagged **Outsource**, sent to the configured vendor with their lead time, and the next operation starts after the vendor returns it.
5. If job work is not allowed (assembly, testing, panel wiring, TC coating), the operation is planned in-house and marked **Late**, so the risk shows on the project.

Daily capacity = shift hours x machines x efficiency, less holidays.

## Talking points for his direct questions

**Planning module standalone first.** Yes. The two planners use only Manufacturing and Project Planning. Production orders come in from the current ERP through Odoo's import (Excel) or API; the plan goes back through the export. Users in that phase: the two planners. The HOD reads exports or a shared dashboard and needs no licence if he does not log in.

**Integration with the current ERP and SAP.** Three routes, in order of effort: Excel import and export (works on day one, no code), scheduled file exchange on a shared folder or SFTP, and API to API (Odoo exposes JSON-RPC and XML-RPC; SAP side via its own interfaces). Scope the route with his IT once we see the current ERP's export options.

**Tally.** Accounting can stay in Tally during phase one. Sales invoices, purchase bills and job-work bills sync to Tally through Ochre's Tally connector or Tally XML vouchers. When the full ERP goes live, Odoo Accounting replaces the double entry he does today.

**Who hosts the database.** Two options. Odoo.sh: hosted and managed by Odoo S.A. with backups, staging branches and upgrades included; the hosting region is chosen when the project is created. Or his own cloud (AWS or Azure India region) or own server, with Odoo Enterprise licence and Ochre managing it. Either way the database belongs to Swaraj and can be exported at any time.

**Implementation, data cleanup and export.** Four to six weeks for planning-only:
1. Week 1: extract from the current ERP (item master, BOMs, routings, machines, open orders, stock). Clean: duplicate items, inactive codes, BOMs with missing levels, routings without times.
2. Week 2: load into a staging copy, reconcile item and BOM counts with the source, sign off.
3. Weeks 3 to 4: capacity setup per machine, two planners run Odoo in parallel with the current process on live projects.
4. Weeks 5 to 6: cut over planning, fix the export format with his IT, train, hand over.

Full ERP (sales, purchase, inventory, Unit 2 go-live, accounting replacing Tally) follows as phase two.

**Against SAP.** Same BOM, MRP and capacity concepts. The difference he will feel: the planning screens above were configured in days, the planners can change rules without a partner change request, and licence plus implementation cost sits well below SAP for 100 employees across two units.

## Honest boundaries

- Day-wise finite capacity with the outsourcing rule is Ochre's add-on on standard Odoo MRP. Standard Odoo schedules work orders against work centre calendars but does not make the outsource decision on its own.
- Capacity is planned in hours per day per work centre, not by minute or by individual machine operator. Operator-level skills can be added in phase two.
- Setup times, tool changes and maintenance downtime are not modelled in the demo; they can be added as capacity deductions.
