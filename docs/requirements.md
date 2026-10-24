# Papradit & GPT Operations App — Requirements for Codex

Version: 1.2 · 24 October 2026 · Owner: Palida

## Selected development stack — approved by the owner

This section records the stack accepted by the owner on 24 October 2026. It overrides earlier suggestions to choose a framework or require a separate managed identity provider. Preserve the module boundaries and business rules below.

### Version baseline

| Component | Selected version | Purpose |
|---|---|---|
| Python | **3.13.17** | Application runtime. |
| Django | **5.2.18 LTS** | Backend, templates, forms, ORM, migrations, authentication and permission foundation. |
| PostgreSQL | **17.11** | Shared SQL database for application records and sessions. |
| Psycopg | **3.3.6**, with the `binary` extra | PostgreSQL driver. Verify a wheel exists for the selected container architecture. |
| HTMX | **2.0.11** | Partial-page form/table updates. |
| Bootstrap | **5.3.8** | Responsive UI components and styles. |
| Gunicorn | **26.2.0** | Production WSGI application server for Django. |
| WhiteNoise | **6.12.0** | Serve collected application static assets. |
| Docker Compose | **v2**, maintained patch release | Local application + PostgreSQL environment. Record the tested CLI version in the README. |

These are the selected starting pins, not a claim that they are the latest releases indefinitely. Compatibility was checked against publisher documentation during planning; this combination has **not yet been installed and integration-tested in the actual Django project**. Codex must validate resolution, image availability and runtime behavior before claiming readiness. If a selected pin is unavailable or has a relevant security issue, document the evidence and propose the smallest compatible change; do not silently substitute arbitrary versions.

### Python dependencies

Initial direct runtime requirements:

```txt
Django==5.2.18
psycopg[binary]==3.3.6
gunicorn==26.2.0
whitenoise==6.12.0
```

Use a committed lock file that includes resolved transitive dependencies and hashes, generated for the selected Python runtime/container platform. The four direct pins above are not a complete transitive lock. Keep development/test dependencies separate. Do not install `psycopg2` alongside Psycopg 3 without a demonstrated requirement.

Use Django's built-in test framework initially for domain and permission tests. Add a browser-testing tool only when implementing the corresponding journeys, then pin and lock its dependencies. Libraries for spreadsheet import, PDF generation or storage should be added only when those features are implemented and their compatibility is checked.

### Frontend and authentication

- Build the operational UI using **Django Templates + HTMX + Bootstrap**, with a single same-origin application.
- Vendor the selected Bootstrap and HTMX assets into versioned application static directories. Serve them using WhiteNoise after `collectstatic`; avoid a mandatory frontend build system for the initial release.
- Use Bootstrap's bundle where components require JavaScript; do not separately duplicate its bundled Popper dependency.
- Use **Django Authentication, Groups/Permissions and database-backed Sessions** for the initial login system. Do not require ChatGPT sign-in or Cognito for this release.
- Keep authentication on the maintained Django implementation. Add application account activation, controlled administrator bootstrap, invitation/password-reset flow, login throttling and the module/action permissions specified below. Do not invent password or session protocols.
- Module access, financial-field access and posting/reversal authority still require explicit server-side application checks; built-in model permissions alone do not satisfy every requirement.
- Use secure session cookies and CSRF protection. Configure session/sign-out behavior and account deactivation consistently across ECS tasks.
- Django Admin is for trusted administration/catalogue maintenance; provide purpose-built forms for รับจ่ายงาน, stock movements and cutting.
- React, FastAPI, Redis, Celery, a separate API service and Django REST Framework are outside the initial baseline. Add them only for a demonstrated later requirement.

### Development and AWS deployment

| Environment/component | Approved baseline |
|---|---|
| Local development | Docker Compose v2: Django app + PostgreSQL 17.11, with persistent local database volume. |
| Source ownership | Owner's GitHub repository. |
| Production image | Linux Python image containing the approved Python patch, with a verified supported distribution and architecture. Resolve an actual available official image tag and pin its digest; do not invent a digest or assume a patch-specific tag exists. |
| App hosting | AWS ECS Fargate, running Django through Gunicorn. Start with a small appropriately measured task configuration. |
| Database hosting | Amazon RDS for PostgreSQL 17.11, private connectivity from the app. Verify the engine version is orderable in the selected AWS Region before provisioning. |
| CI/CD | GitHub Actions → checks/tests → Docker build → Amazon ECR → ECS deployment. |
| Application static assets | WhiteNoise, included in the built image after `collectstatic`. |
| Uploaded business files | If implemented, use durable access-controlled storage such as S3; do not use WhiteNoise or ephemeral container disk for private uploads. |
| Sessions | PostgreSQL-backed shared Django sessions. No Redis dependency initially. |
| Secrets | Deployment-injected environment/secrets configuration; no credentials in Git or images. |

Use one modular application and one PostgreSQL database, not a service/database per module. Separate development/test/production databases. Keep local and production PostgreSQL versions aligned, subject to verified RDS availability and controlled patch upgrades. Choose the HTTPS entrypoint, networking, logs and backup retention with an explicit total-cost estimate; ECS task cost alone is not the complete production bill. Do not provision paid resources solely because this stack is documented.

### Required compatibility and release checks

1. Resolve and lock dependencies under the selected Python/container architecture; run `python -m pip check`.
2. Build the container from a verified image digest and scan application/image dependencies for known relevant vulnerabilities.
3. Run `python manage.py check`, migration-consistency checks and migration execution against a fresh PostgreSQL 17.11 test database.
4. Run application tests against PostgreSQL, including permissions, price snapshots, stock ledger, idempotency and concurrent issue/return cases. SQLite-only tests do not verify production stock concurrency.
5. Run `collectstatic`, start Gunicorn and verify static assets, authenticated page rendering and health checks.
6. Run Django deployment checks with production settings and verify HTTPS, secure cookies, CSRF, allowed hosts and trusted-proxy configuration.
7. Confirm records and sessions survive app-container replacement; test backup restoration separately.
8. Record the tested image digest, resolved dependency lock, Python/PostgreSQL versions and CI results. Never describe planning/documentation checks as a successful runtime test.

### Publisher references used for this baseline

- Python 3.13.17 release announcement: https://blog.python.org/2026/10/python-3151-3149-31317/
- Django supported release series: https://www.djangoproject.com/download/
- Django 5.2 Python compatibility: https://docs.djangoproject.com/en/5.2/releases/5.2/
- Django 5.2 PostgreSQL/driver compatibility: https://docs.djangoproject.com/en/5.2/ref/databases/
- Psycopg release metadata: https://pypi.org/project/psycopg/
- Gunicorn release metadata: https://pypi.org/project/gunicorn/
- WhiteNoise requirements: https://whitenoise.readthedocs.io/en/stable/
- HTMX installation/version: https://htmx.org/docs/
- Bootstrap installation/version: https://getbootstrap.com/docs/5.3/getting-started/introduction/
- RDS PostgreSQL release calendar: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-release-calendar.html

---

## 0. Authoritative module contract — owner update, 24 October 2026

This section records the owner's latest requirements and takes precedence over earlier grouping, sequencing and optional architecture choices below. Build the app in modules, releasing **รับจ่ายงาน first**. Do not implement all later modules before delivering and validating this first operational module. Existing source-field mappings and batch correctness rules below remain applicable.

### 0.1 Confirmed requirements

- Internal web app for 1–10 users, with remote browser access.
- Deploy application containers using **Docker on AWS ECS**.
- Persist business records in a **SQL database**. Proposed concrete default: PostgreSQL, hosted separately from application containers; use Amazon RDS for the production deployment unless the owner selects another SQL hosting option.
- One Admin area manages who may log in and which modules/actions they may access.
- Separate the four operational modules from five catalogue/price modules.
- The original folders and historical data remain unchanged until an approved, reconciled migration.

### 0.2 Module registry and release order

| ID | UI module | Responsibility | Release |
|---|---|---|---|
| `admin` | ผู้ใช้และสิทธิ์ / Admin | Accounts, invitations, activation/deactivation, module/action grants and audit visibility. | Foundation, before real users access Module 1. |
| `catalog.products` | Catalog สินค้า | Products, categories, sizes/variants and product-price history where relevant. | Minimal required fields with Module 1; complete price functions incrementally. |
| `catalog.jobs` | Catalog งาน | Reusable job/customer specifications and pattern/work-step definitions; not actual PR transactions. | With Module 1. |
| `catalog.wages` | Catalog ค่าแรง | Work-step wage rates and history, optionally by worker/supplier and price type. | With Module 1. |
| `catalog.fabrics` | Catalog ผ้า | Fabric codes, descriptions, colors/specification, units and price history. | With Module 2. |
| `catalog.materials` | Catalog วัตถุดิบ | Non-fabric material codes, categories, units and price history. | With Module 3. |
| `work` | รับจ่ายงาน | PR receipt/lines, work-step assignments, partial receipts, QC, remaining quantities and applied wages. | Operational Module 1 — build first. |
| `fabric` | เบิกคืนผ้า + ห้องตัด | Batch receipts, issues, returns, cutting allocations/output, waste and batch balances. | Operational Module 2. |
| `materials` | เบิกคืนวัตถุดิบ | Non-fabric receipts, issues, returns and job/PR balances/costs. | Operational Module 3. |
| `fixed_costs` | ต้นทุน Fix cost | Fixed-cost entries by period/category and separately approved allocation rules. | Operational Module 4. |

Keep one clear sidebar grouping for operations, one for catalogues/prices, and one for Admin. Unreleased modules must be clearly unavailable or hidden, rather than presented as working features.

### 0.3 Architecture boundaries

Use a **modular monolith**: one codebase, one deployed web application/service initially, and one PostgreSQL database. Organize domain code and APIs by module, with shared identity, auditing and master data. Modules do not mean separate ECS services, separate databases or microservices.

Suggested repository boundaries:

- `modules/admin` — account membership, module grants and administration.
- `modules/catalog` — products/jobs/wages/fabrics/materials and price histories.
- `modules/work` — requests, lines, assignments, receipts and QC.
- `modules/fabric` — batches, fabric ledger and cutting.
- `modules/materials` — non-fabric stock ledger and allocations.
- `modules/fixed-costs` — periodic fixed costs and allocation results.
- `shared` — identity helpers, database access, audit, files and UI building blocks.
- `infra` — Docker, ECS deployment definitions and environment configuration.

These are conceptual boundaries, not a mandate for a specific framework directory layout. Use foreign keys/shared identifiers across modules. The running application must not depend on ChatGPT Sites, D1 or a signed-in ChatGPT session to function on AWS.

Logical deployment: browser → HTTPS application entrypoint → ECS app tasks → PostgreSQL database. The database must not be internet-accessible; only authorized application/network identities may connect. Application containers are replaceable and stateless. Do not run the production database inside the app task or rely on container-local disk for durable records. Keep database credentials and other secrets outside the image/repository. Attachments, if implemented, need durable access-controlled storage.

Prepare a local Docker Compose app + PostgreSQL environment, then a production ECS deployment package. ECS Fargate is the proposed initial compute option; explain configuration, operational tradeoffs and current costs before paid provisioning. Supply documented backup/restore, health checks, logs, migration procedure and GitHub CI/CD. A single SQL database is adequate as the initial design; no warehouse or dbt pipeline is required to operate this transactional app.

### 0.4 Operational Module 1 — รับจ่ายงาน

**Goal:** replace entering and tracking production work in รับจ่ายงาน before adding stock movements.

Required screens:

1. PR list and PR detail, searchable by PR, PO, job/customer specification, product, requester, due date and status.
2. Receive/create a PR header and multiple product/size lines, preserving original `pp_id`, `pr_list_id` and other source IDs through an explicit mapping.
3. Select work steps from Catalog งาน/ค่าแรง and assign quantities to workers/suppliers.
4. Receive completed work in partial quantities; record QC acceptance/rejection/rework.
5. Track quantity assigned, received, accepted, still with worker and available to assign, per PR line/work step.
6. Show applied unit wages and calculated labor amounts only to users with financial-read permission.
7. Operational dashboard and export, with overdue/incomplete work clearly visible.

Required master data: product, job template, pattern/work step, wage rate, supplier/worker and relevant requester/assigner references. Supplier/worker management can be a shared master-data screen; do not invent a sixth price catalogue without a business need.

Transactions must capture the applied wage rate at the agreed posting event; later catalogue changes must not recalculate historical work. Separate work/QC status from wage settlement status.

The owner has not yet requested a full wage payment/accounting system as the first release. Preserve source payment-status/reference fields where needed, but schedule invoice generation, partial payments, payment approvals and PO approval workflows as separate follow-up scope unless specifically confirmed as essential to รับจ่ายงาน. Do not block Module 1 on those enhancements.

Module 1 must work when `fabric`, `materials` and `fixed_costs` are unreleased. Fabric/material descriptions may be captured as reference information, but no unimplemented stock movement should be implied. Preserve future PR-line integration points.

### 0.5 Operational Module 2 — เบิกคืนผ้า + ห้องตัด

Build on Module 1 PR/line identifiers and Catalog ผ้า. Apply the batch ledger, original-issue return rules, quantity validation and cost distinction in section 5.

Provide batch/receipt entry, available-stock view, issue to PR/work, unused-fabric return to the original issue/batch, cutting sessions, per-size garment output, consumption/waste and remaining fabric held by cutting. Show both warehouse balance and cutting-held balance.

A material master, supplier lot, receipt-cost batch, roll and cutting session are different entities. Confirm which optional roll/remnant detail is needed. Use database transactions, immutable posting/reversals and idempotency to prevent double submissions and negative stock. A receipt can contain multiple batches; a cutting session can use multiple batches with explicit allocation lines.

### 0.6 Operational Module 3 — เบิกคืนวัตถุดิบ

This module handles **non-fabric materials**, for example buttons, zips, labels or packaging if those categories are confirmed from the source catalogue. Fabric stock belongs to Module 2; do not maintain two independent stock balances for the same item.

Required screens/actions:

- Material receipts with supplier/document/date, quantity, unit and frozen receipt cost.
- Issue material to a PR/PR line, job or approved cost object.
- Return unused material linked to the original issue and original valuation.
- Display balances and movement history by material and optional lot/location.
- Record consumption, scrap and authorized adjustments/reversals where used.
- Report net issues, unconsumed balances and consumed cost per PR/job.

Validate quantity precision per unit: pieces may require integers, while metres/weight may be fractional. Define supported conversions explicitly. Do not aggregate incompatible units. Reject over-issues and returns above eligible outstanding quantities, including concurrent submissions.

Proposed valuation for the initial design: explicit receipt/lot allocation with costs retained from the original issue. Confirm FIFO, weighted average or specific identification before implementing automated cost selection. The absence of a confirmed method must not be hidden behind an arbitrary average.

### 0.7 Operational Module 4 — ต้นทุน Fix cost

Required fields: cost ID/reference, company/context if applicable, cost category, description, accounting/business period, amount, currency, applicable tax convention, source/reference document, status and actor/time. Examples such as rent or salaries are proposed categories, not confirmed source data.

Provide list/create/edit-draft/post/reverse, period/category totals, and a traceable cost report. Prevent duplicate import/posting by source identity or idempotency key.

Keep **fixed-cost recording** separate from **allocating fixed costs to jobs**. Provide an allocation policy and calculation preview only after the owner confirms the basis (for example, labor hours, production units or another driver). Store the approved period, source pool, driver quantities, denominator, allocation results and rounding residual. Allocated total must reconcile to the approved pool, with an explicit unallocated amount where necessary. Never charge the same pool twice or add raw fixed cost and its allocated value twice to one report.

Recording fixed costs may ship before allocation is configured. Reports must then show those costs as unallocated rather than silently inventing cost per garment.

### 0.8 Five catalogue/price modules

Each catalogue has its own permission key and maintenance screen. A catalogue is a shared definition/rate source, not a transaction ledger.

| Catalogue | Core data | Price/rate dimensions to validate |
|---|---|---|
| สินค้า | Product ID/code/name, category, active flag, sizes/variants. | Selling/transfer price where applicable; company, customer/job, currency, unit and tax treatment. Do not confuse it with manufacturing cost. |
| งาน | Job/template ID/name/specification; patterns and work steps. | Job/quotation/template price if used. Confirm whether งาน means customer specification, service or a reusable production template. Actual PRs remain in Module 1. |
| ค่าแรง | Work-step reference, pattern/job, price type, supplier/worker scope where applicable. | Wage per accepted/assigned/received piece according to the agreed payable policy. |
| ผ้า | Fabric code/name/specification/color, base unit, active flag. | Supplier/quoted purchase prices and effective dates; receipt batch cost remains independently frozen. |
| วัตถุดิบ | Material code/name/category, base unit, active flag. | Supplier/unit/currency purchase prices and effective dates; issued costs follow the chosen valuation method. |

Common price requirements:

- Store a stable catalogue identity and separate price versions, not one repeatedly overwritten price field.
- Price version fields: amount, unit, currency, effective-from date, effective-to date (optional), applicable dimensions, creator and audit metadata.
- Reject overlapping active periods for the same price key; define intervals consistently, such as `[effective_from, effective_to)`.
- When creating a transaction, select the applicable price by its business date and dimensions. If none matches or several match, require resolution; never silently use today's rate for a past transaction.
- Save the applied amount and price-version reference on the transaction. Posted financial values are not changed by later catalogue edits.
- If an historical price is corrected, retain audit history and require an explicit adjustment/reposting decision rather than mass recalculation.
- Define whether zero means free, how missing prices are represented, and required monetary precision.
- Deactivate referenced catalogue items rather than deleting their identity.

### 0.9 Admin: login eligibility and module-level access

Authentication answers **who the user is**; application access control answers **whether that user may log in and what they may do**. Implement both server-side.

Admin functions:

- Invite/create approved user accounts through the selected identity system.
- Activate/deactivate app access; no unrestricted registration by default.
- Assign roles and module/action grants; show a permission matrix for all ten module keys in section 0.2.
- Review last-login information when available and relevant audit history.
- Manage account/session revocation using the identity provider's supported workflow; do not expose stored passwords.

Permission model:

- Minimum actions: `read`, `create`, `update_draft`, `post`, `reverse`, `export`.
- `approve` is optional per workflow and separate from posting; no implied approval authority.
- Add explicit `read_financial` and `manage_prices` where relevant. A user allowed to work in รับจ่ายงาน need not see wages or selling prices.
- `admin.manage_users` and `admin.manage_permissions` must be separately guarded; ordinary module editors cannot grant themselves access.
- Deny by default. A role is a reusable bundle of module/action grants, not a substitute for module checks.
- Default to additive role grants without explicit deny overrides for the initial design; document the effective-permission calculation.
- Protect the final active administrator from accidental deactivation/demotion.
- Enforce rights on server APIs, reports, search, exports and attachments, as well as page/menu visibility.
- Read-only catalogue lookup needed by an operational form must be explicitly authorized. If a user may use รับจ่ายงาน but cannot manage Catalog สินค้า, permit only the necessary product-ID/name lookup through a defined permission; do not leak price fields or grant catalogue edit access implicitly.
- Audit account changes and permission changes, with actor, target, old/new values and time.

Examples: an operator may receive/assign work in `work` while having no `fabric` or `fixed_costs` access; a cutting user may use `fabric` with limited PR/product lookup and no wage visibility; a finance user may read selected operations and manage `fixed_costs` without administering logins. Actual accounts/grants require owner-provided identities.

### 0.10 Cross-module integration and acceptance

Use stable IDs, foreign keys and explicit read contracts. PR/PR-line identity from Module 1 is the shared cost/work reference for fabric, materials and optional fixed-cost allocation. Catalogue price changes cannot rewrite posted transactions in any module.

Additional acceptance criteria:

1. Module 1 runs and persists records through Docker + PostgreSQL while later operational modules are disabled.
2. An activated user with only `work.read` can read permitted work but cannot create, post, export or call another module's API unless separately granted.
3. Hiding a module in the UI is not sufficient: direct unauthorized requests return forbidden with no data changes.
4. Revoking access or disabling an account takes effect under the documented session policy; API checks do not rely solely on a stale menu/session permission list.
5. Catalogue editors can change future prices without changing existing posted wages, batch costs or material costs.
6. Fixed-cost recording works without an allocation method and reports its unallocated amount honestly.
7. Restarting or replacing ECS app tasks does not lose database records or uploaded files.
8. A first-time deployment cannot grant administration to an arbitrary first visitor.
9. Price/financial fields remain absent from responses and exports for users without the corresponding grants.
10. Test and production use separate databases/configuration. Database backups have a documented and tested restore path.

**First implementation request:** deliver the Admin/auth foundation, the minimum product/job/wage catalogues and shared worker master, and **Module 1 รับจ่ายงาน** with working SQL persistence and tests. Establish schema/API boundaries for Modules 2–4, but implement them in the order listed after the preceding release is validated. Do not treat payment accounting, Odoo integration, historical full migration or every old spreadsheet formula as a prerequisite to this first working release.

---


## 1. Instructions to Codex

Build an internal web application to replace the operational spreadsheets in Papradit_DB and GPT_DB, and add fabric batch inventory and authenticated user access.

This document is your standalone specification. You do not need Google Drive access to begin. Do not claim you have inspected files you cannot access. Use the field inventory below for implementation; use uploaded workbook/CSV exports for complete migration and formula inspection. Never invent historical records, prices, identifiers, balances or opening stock.

Start by reading this entire document and inspecting any repository supplied. Produce a short implementation plan, proposed relational model, and a list of unresolved business decisions. Then implement the parts that do not depend on those answers. Ask focused questions only when a decision would change data meaning, authorization or a financial result. Routine implementation choices do not require approval.

Deliver working backend APIs, persistent PostgreSQL storage, real authentication, application permissions, usable forms, reports, migrations, tests and deployment documentation. Mark incomplete requirements explicitly. A static mockup, localStorage-only app or fake login does not satisfy this specification.

If this repository contains the earlier Sites prototype, treat it as a UI reference and partial proof of concept. It is not the target production architecture or an authoritative migration source. Its historical database is empty unless independently verified. Do not inherit its limitations, including broad status lists, free-text relationships or first-login administrator creation for a shared app.

## 2. Business context and scope

- Small garment business with two business contexts: Papradit / PPD (production) and GPT (sales/customer orders). Confirm the legal-company boundary before implementing strict company isolation or intercompany accounting.
- Intended users: 1–10 people, accessing remotely through a browser.
- Primary tasks: maintain products and job templates; record PO/PR demand; allocate work to workers/suppliers; track QC and delivery; record wages and payments; receive, issue, cut and return fabric; track job costs.
- Current operations use Thai spreadsheets, repeated dropdown descriptions and spreadsheet formulas across multiple files.
- Target: deploy an independently maintainable application to the owner's AWS account, with source in the owner's GitHub repository.
- Future: possible Odoo integration. Keep stable business IDs and exportable data; no Odoo dependency in the first release.
- Build for correctness, safety and low maintenance. Do not promise a one-day production cutover.

### Evidence classification

| Label | Meaning |
|---|---|
| Observed | Seen in folder listings, workbook metadata, or bounded header/sample reads during this conversation. Complete workbooks and formulas were not audited. |
| Requested | Explicitly requested: replace both folder workflows, fabric batch features, login, remote use, small team, future Odoo and AWS direction. |
| Proposed | A concrete starting design to implement subject to the decisions identified below. It is not a claim that staff already follow that rule. |
| Unverified | Must be checked from exports or with the owner before migration/cutover. |

## 3. Source inventory and field mapping

Keep Thai labels supported in the UI, but use consistent English names in database/code. Prefer Thai UI by default with English technical identifiers where useful. Confirm language preference during review.

### Papradit_DB

Observed operational workbooks and areas:

1. **รับจ่ายงาน** — requests, work selection, assignments, tracking, wage/QC status.
2. **ClothingModel** — pattern catalogue and standard work-step/wage definitions.
3. **จ่ายค่าแรง** — wage payment periods/invoices.
4. **ต้นทุน** — fixed costs, other costs, template costs and material costs in subfolders.
5. **Stock** — inventory-related folders; the detailed contents have not been audited.
6. **Storage** — archived workbook/template areas; do not import archives as live records by default.
7. **ใบจ่ายค่าแรง** — wage documents folder; document formats and contents remain unverified.

### GPT_DB

1. **งานและสินค้า** — product catalogue and job/customer templates.
2. **PO_Approval** — PO references, quantities, requesters and an approval column. Existing approval rules are unverified.

### Observed source fields

| Workbook / tab | Observed fields and interpretation |
|---|---|
| รับจ่ายงาน / รับPR | `pr_list_id`, PO date, PO sequence, `PO_No`, `PR_No`, `PI NO`, job name, product name, fabric, color, size, quantity, requester, production request date, delivery date, PPD invoice/date, `PRICE PPD TO GPT`, GPT invoice/date, `PRICE PPD TO GPT 2`, material-issued/awaiting-cutting flag, cutting/sewing flag, receipt date, `pp_id`, `ps_id`, `VALID`, descriptive concatenated keys. |
| รับจ่ายงาน / ขั้นตอนการจ่ายงาน | `assign_id`, assigned job description, remaining quantity, assigned quantity, supplier, assigner, QC status, wage/payment status, assignment date, payment due date, PR number, work step, unit wage, total wage, `SupplierID`, `job_id`, `pr_list_id`, `pp_id`, supplier type, wage type, `task_id`. |
| ClothingModel / รูปแบบงาน | `pattern_id`, pattern name. |
| ClothingModel / ขั้นตอนงาน | `task_id`, job template, pattern, note, price/wage type, wage amount, concatenated work-step descriptions. |
| จ่ายค่าแรง / ตารางค่าแรง | invoice number, payment period, supplier display name, supplier name/ID, bill issuer/assigner name, payment date, submit flag, PDF reference. No reliable invoice amount was established from this bounded read. |
| งานและสินค้า / สินค้า | `product_id`, product name, product category. |
| งานและสินค้า / ชื่องาน | `template_id`, category/type, job/template name, description. |
| PO_Approval / PO_No | `PO_id`, PO number, job name, product name, quantity, requester, approval field. |
| ต้นทุนผ้า / เบิกคืนผ้า | `cwd_id`, issue/return date, PR-product description, fabric description, notes, issue/return type, quantity, second note, unit, `pp_id`, `fabric_id`. No explicit batch ID was observed in these columns. |
| ต้นทุนผ้า / ห้องตัด | `pattern_id` (meaning must be verified), date, PR-size description, fabric description, notes, total fabric quantity, unit fields, garment quantity, `pp_id`, `fabric_id`, `pr_list_id`. Some continuation rows have blank dates. |

Important interpretation rules:

- Do not assume similarly named IDs in different workbooks have identical meanings.
- `pp_id`, `ps_id`, `pr_list_id` and the cutting-sheet `pattern_id` need an explicit identity map.
- Preserve `PR_No`, PO numbers and source identifiers as strings, including leading zeros.
- Do not use concatenated names such as `PR + job + product + size` as relational primary keys. Link stable IDs and generate labels for display.
- Existing source warnings about `+` in descriptions indicate a delimiter dependency. The app must safely support ordinary punctuation, Thai text and spaces without breaking relationships.
- Clarify the meaning of both PPD-to-GPT price columns before treating either as revenue or cost. A value such as `Free` must not silently become an unknown, missing or paid price.
- Do not treat `VALID=FALSE`, blank continuation rows or historical archives as deletions without an agreed migration rule.

## 4. Required application modules

### 4.1 Dashboard and navigation

Provide a clear dashboard and searchable sections for orders/POs, production requests, fabric batches, inventory movements, cutting, assignments/QC, wages/payments, cost reports, catalogues, users and audit history.

Dashboard totals must come from persisted records, respect permissions, and have a defined period/filter. Distinguish stock on hand, fabric held in cutting, actual consumption and garment output. Show an honest empty state rather than fabricated transactions.

### 4.2 Master data

Maintain products, categories, job/customer templates, garment patterns, work steps, fabric, colors, suppliers/workers and units. Referenced master data should be deactivated rather than deleted.

Fabric fields: ID/code, name, color reference where applicable, base unit, optional width/composition and active flag. Work-step rates need effective dates if rate history is enabled. Every assignment must retain a snapshot of its applied rate so later master changes do not alter historical wages.

Separate a job/customer template from a production work-step template. Preserve any original IDs for import/export lineage.

### 4.3 PO and PR management

- PO header and multiple PO lines: number, company/context, requester, customer/job template, product, quantity, dates and approval state.
- PR header and multiple PR lines: PR number, linked PO line when available, product, fabric/color where known, size, requested quantity, production date and due date.
- Permit partial production, work allocation and deliveries. Do not mark an entire PO/PR completed after a partial delivery.
- Support explicit cancelled/closed states with reasons. Avoid destructive deletion of referenced orders.
- Proposed PO workflow: draft → submitted → approved/rejected. Approved changes create a revision or require reapproval. Confirm who may approve and whether self-approval is permitted.
- Statuses for production, QC, delivery, invoices and payment are distinct; do not put them into one interchangeable status dropdown.
- Provide overdue and remaining-quantity views.

### 4.4 Work assignments and QC

Assign a PR line/work step and quantity to a worker or supplier. Record assigner, assignment date, expected completion, unit wage, wage type and payment due date.

Prevent allocation beyond remaining demand for the same PR line/work step unless an authorized rework/override is recorded. The same garment may legitimately pass through several different work steps; do not subtract all work-step quantities from one shared balance.

Record partial received quantities, accepted quantities, rejected/rework quantities and QC actor/time. Define payable quantities from the agreed QC/payment policy. Do not silently assume all assigned pieces are payable. Show the calculation and applied rate.

### 4.5 Wage invoices and payments

Group eligible assignment results into wage invoices by worker/supplier and payment period. Include invoice number, lines, applied rates, payable quantities, total, issuer, approval state and payment references.

Support partial payments and outstanding balances. Calculate payment status from payments, rather than editing an unrelated `Paid` label. Prevent including the same payable quantity in two invoices. Separate approving a wage invoice from recording its payment.

Generate a printable/downloadable wage statement with Thai text. Match the existing wage-document layout only after a sample is provided; do not claim layout parity before inspection.

### 4.6 Other costs and costing templates

Record fabric cost, labor, other materials, fixed-cost allocation and miscellaneous costs separately. Fixed-cost allocation needs an agreed basis and period; do not invent an allocation rule.

Maintain estimated/template costs separately from actual job costs. Record currency, tax treatment and whether values include VAT once confirmed. Show assumptions clearly and avoid treating PPD-to-GPT transfer prices as actual manufacturing cost without confirmation.

## 5. Fabric batch and cutting rules

The following is a **proposed model**, not a verified existing batch policy.

### 5.1 Fabric, lot, receipt batch and roll

- A fabric master identifies the material; it can have many receipt batches.
- Proposed stock batch: one fabric, one color, one base unit and one frozen receipt cost. Different receipt costs create separate stock batches even if the supplier lot is the same.
- Keep supplier lot/dye-lot as a separate attribute from the internal stock batch ID.
- An optional roll record belongs to one batch. A receipt document may contain several fabrics/batches/rolls.
- A cutting session may use several batches, potentially several fabrics, with explicit allocation lines. Do not confuse a cutting session with a stock batch.
- Provide a human-readable batch code and an immutable internal ID.
- Confirm whether individual roll tracking is required before enabling it; do not infer roll IDs from free-text notes.

Receipt fields: batch code, fabric, color, supplier, supplier lot, receipt reference/date, quantity, unit, unit cost, warehouse/location and optional roll details. Freeze the financial value on posting. Corrections use authorized reversal/adjustment workflows.

### 5.2 Ledger and validation

Use an inventory ledger with receipt, issue-to-cutting, return-from-cutting, consumption, waste, adjustment and reversal semantics. Preserve actor, event time, business date, source reference, reason and idempotency key.

- An issue must reference an existing batch and PR/job allocation, and reduce warehouse stock.
- Reject issues that exceed available stock. Concurrent issues must be checked inside the database transaction, not only in the UI.
- A return must reference its original issue. It inherits that issue's batch, material and original cost, and cannot be used to move stock into another batch silently.
- Do not allow returned + consumed + wasted quantity to exceed the original issue's quantity, net of valid reversals.
- Cutting consumption changes work-in-progress into consumption; it must not deduct warehouse stock a second time.
- A transfer between jobs/locations requires its own linked movements and authorization.
- Posted transactions are immutable; reversals retain the original entry and audit trail. Use a dedicated opening-balance import instead of inventing historical receipts.
- Validate units; never add metres and yards directly. Confirm whether yards/kg are used. Default initial release to metres, with unsupported units blocked rather than silently relabelled.
- Use decimal/integer quantity arithmetic and fixed-precision currency, not binary floating point for persisted financial calculations. Proposed precision: 0.001 m; unit-cost precision must accommodate actual supplier invoices and should not be restricted to two decimals without confirmation.

### 5.3 Cutting session

A cutting session has date, operator, source issue allocations and output lines by PR/product/size. Record fabric consumed, waste, unallocated balance and garment output. One session can draw from multiple issues; one issue can support multiple sessions.

Returns of usable remnants go back to the original batch, optionally with a remnant/roll identifier. Waste is not a return. Record how common fabric consumption and waste are distributed across sizes/jobs; leave unallocated cost visible until an approved basis is supplied.

### 5.4 Quantity and cost equations

Use base units and clearly distinguish quantities:

- Warehouse on hand = receipts + returns + inward adjustments/transfers − issues − outward adjustments/transfers, including valid reversals.
- Cutting-held balance per issue = issued − returned − consumed − wasted, net of reversals.
- Net issued fabric value for a PR = issued value − returned value. This includes fabric still held in cutting.
- Actual consumed fabric cost = allocated consumed quantity × original batch unit cost; report waste cost separately and include it according to the agreed costing policy.
- Total actual job cost = agreed fabric consumption/waste cost + recognized labor cost + other direct costs + approved overhead allocation.
- Do not add wage payments to labor cost again when the labor has already been recognized from accepted work/invoice lines.

Example, excluding tax: receive 100 m at THB 150/m; issue 80 m to PR-A; consume 45 m and waste 5 m; return 20 m. Warehouse on hand is 40 m. Cutting-held balance is 10 m. Net issued value is THB 9,000; consumed plus waste cost is THB 7,500; remaining cutting-held value is THB 1,500. Those figures must not be presented as the same metric. Returning another 11 m is rejected until another valid transaction changes the balance.

## 6. Login, roles and access

Use real individual user accounts with Django Authentication and database-backed Sessions, as approved in the selected stack. Support invitation, login, logout, password reset if passwords are supported, account deactivation and session expiry. Never store plaintext passwords or include credentials in code. Do not implement a home-grown authentication protocol.

Bootstrap the first administrator through a controlled deployment command/invitation, not whichever visitor logs in first. Disable unrestricted self-registration by default.

Proposed permissions; confirm specific staff responsibilities before assigning actual accounts:

| Role | Access |
|---|---|
| Admin | Manage users/roles, configuration and all workflows; view audit history. |
| Operations | Maintain operational master data, PRs, batch quantities, issues/returns, cutting and work assignments; no user administration. Financial visibility needs explicit permission. |
| Finance | View approved operational records; maintain costs, wages/invoices, payments and financial reports; no unrestricted stock adjustments. |
| Approver | Approve permitted PO/invoice/adjustment workflows; can be an additional permission rather than a separate exclusive role. |
| Viewer | Read-only access to explicitly permitted records/reports. |

Enforce authorization server-side on every endpoint and export, including company visibility and field-level financial restrictions. Hiding buttons alone is insufficient. Invitations in the database alone do not grant infrastructure access. Audit role changes, approvals, posted/reversed transactions and financial edits.

## 7. Screens and usability

- Desktop/tablet responsive interface; clear Thai labels and THB formatting.
- Search/filter by PO/PR, job, product, size, worker, fabric, batch, date and status.
- Relational dropdowns use IDs behind readable labels; no manually concatenated keys.
- New receipt, issue, return and cutting forms show live balances and actionable validation messages.
- PR detail shows requested/delivered/remaining quantities, work-step progress, issued/held/consumed fabric, waste, wages and other costs.
- Batch detail shows receipt, rolls if enabled, movements, current stock, original cost and job allocations.
- Use accessible form labels, keyboard navigation, confirmation for destructive/reversal operations and clear loading/error states.
- Provide exportable CSV reports and a permission-scoped backup/export path. Printable wage statements should support Thai fonts.

## 8. Suggested relational model

This is a starting model; refine it in the design plan without losing the required relationships.

`companies`, `users` (external identity reference), `memberships`, `roles/permissions`, `products`, `job_templates`, `patterns`, `work_steps`, `wage_rates`, `suppliers_workers`, `fabrics`, `colors`, `units`, `locations`, `po_headers`, `po_lines`, `po_approvals`, `pr_headers`, `pr_lines`, `deliveries`, `delivery_lines`, `assignments`, `assignment_receipts_qc`, `fabric_batches`, optional `fabric_rolls`, `inventory_events`, `issue_allocations`, `cutting_sessions`, `cutting_inputs`, `cutting_outputs`, `cutting_cost_allocations`, `wage_invoices`, `wage_invoice_lines`, `payments`, `payment_allocations`, `other_costs`, `cost_templates`, `overhead_allocations`, `attachments`, `audit_events`, `import_runs`, `import_row_lineage`.

Use foreign keys, unique constraints, indexed business lookups and transaction-safe posting. All records need stable IDs and relevant created/updated actors/timestamps. Keep event timestamps in UTC and display business dates/times in Asia/Bangkok. Company-specific uniqueness and cross-company relations must follow the confirmed operating model.

Avoid a single generic JSON table for all core entities. JSON is acceptable for import staging or optional metadata; core relationships, quantities, statuses and monetary amounts should be typed and constrained.

## 9. Migration from Google Sheets

Codex may begin without source exports, but migration cannot be declared complete without them.

1. Accept owner-provided `.xlsx` exports preserving all relevant tabs; inspect formulas, validations, hidden lookup tabs and document templates. CSV exports are supported per tab where formulas/formatting are unnecessary.
2. Inventory exact headers, header row numbers and source row counts. Source headers may start on row 2 or 3; do not assume row 1.
3. Stage raw values with file/tab/row provenance before transformations. Keep original IDs and raw values.
4. Profile missing IDs, duplicate business keys, invalid dates/units, orphaned references and inconsistent descriptions. Report conflicts; do not silently discard rows.
5. Parse dates using explicit source rules. Samples use day/month/two-digit-year formats. Verify Gregorian/Buddhist-year conventions rather than applying a universal offset. Preserve blank continuation dates unless a documented fill-down rule is approved.
6. Distinguish blank, zero, `Free`, `-`, `--`, comma-formatted amounts, booleans and invalid values. Create a reviewed mapping per column.
7. Load masters before transactional records. Use an explicit ID crosswalk and retain source relationships.
8. Existing fabric history lacks verified batch assignments. Stage these as unresolved; request a batch mapping or an opening-stock cutover plan. Do not infer supplier lots, batch costs or historical ownership from notes.
9. Import scripts must support dry-run validation, rejected-row reports and idempotent reruns. A rerun cannot duplicate stock events, PR lines or wage invoices.
10. Reconcile source/target counts, PR quantities, wage totals, stock balances and representative job costs. Explain intentional exclusions such as archives and invalid records.
11. Run a reviewed parallel trial, back up data and document the cutover. Do not delete or alter the original folders.

Minimum exports to request when needed: รับจ่ายงาน, ClothingModel, จ่ายค่าแรง, งานและสินค้า, PO_Approval, ต้นทุนผ้า, material catalogue/cost workbooks, template cost workbooks, fixed/other cost files, plus one wage document sample. Additional archive/Stock data is needed only if selected for migration.

## 10. Architecture, deployment and source ownership

- Source code must be committed to the owner's GitHub repository. Do not create a new hosted platform dependency unless explicitly selected by the owner.
- Baseline: one conventional web application and PostgreSQL, with Docker Compose for local app/database development. Prefer a small deployable system over unnecessary microservices.
- Use the owner-approved Django/HTMX/Bootstrap/PostgreSQL stack and version baseline at the top of this document; validate and lock it at implementation time.
- Target AWS deployment. Prepare Dockerfiles, migrations, health checks, environment-variable templates and deployment scripts/infrastructure configuration. Explain the chosen compute, private database connectivity and HTTPS route before provisioning paid resources.
- Application talks to the database server-side. Browsers never receive database credentials or connect directly to PostgreSQL.
- Separate dev/test/prod configuration and databases. Keep secrets outside Git; use least-privilege application and deployment identities.
- The approved Django authentication/session implementation, automated backups with a tested restore procedure, server-side audit logs and basic operational monitoring are required for production readiness.
- If attachments/PDFs require object storage, use access-controlled storage and authorized downloads.
- CI/CD should run meaningful tests, validate/build the app/container, scan for exposed secrets and deploy through a controlled workflow. Database migrations need an explicit rollout/backup strategy; do not run destructive migrations automatically.
- Provide service inventory and a current cost estimate with assumptions before creating AWS resources. No exact cost is asserted by this document.
- Odoo integration is a future API/export boundary; do not use Odoo tables as this app's internal database contract.

## 11. Acceptance tests

| ID | Scenario and expected result |
|---|---|
| AUTH-01 | Anonymous requests cannot read or write business data. API returns an appropriate unauthorized response. |
| AUTH-02 | Viewer attempts a direct write API call: forbidden and no data changes. |
| AUTH-03 | Non-admin attempts role changes: forbidden. Disabled users lose access under the documented session policy. |
| AUTH-04 | Operations user without financial permission cannot obtain wages/costs through API responses, reports or exports. |
| AUTH-05 | Concurrent first visits cannot grant administrator privileges. Admin setup is controlled. |
| ORD-01 | One PO/PR with multiple products/sizes retains distinct lines and correct quantities. |
| ORD-02 | A partial delivery leaves the correct remaining quantity and does not close the whole order. |
| ORD-03 | Renaming a product/job display label does not break existing relationships or change historical rate snapshots. |
| WORK-01 | Assignment limits apply per PR line/work step; sequential work steps are not incorrectly treated as duplicates. |
| WORK-02 | Partial QC acceptance and rework produce the agreed payable quantity and a traceable history. |
| PAY-01 | The same payable work cannot be invoiced twice. Partial payment leaves the correct outstanding balance. |
| PAY-02 | Changing a master wage rate does not recalculate posted historical invoices. |
| FAB-01 | Receive 100 m at THB 150/m, issue 80 m: warehouse has 20 m, cutting holds 80 m. |
| FAB-02 | Two concurrent 15 m issues against that 20 m balance: at most one succeeds. Stock never goes negative. |
| FAB-03 | Apply the example in section 5.4: warehouse 40 m, cutting-held 10 m, net issued THB 9,000, consumed+waste THB 7,500. |
| FAB-04 | A return inherits its original batch/cost; editing the batch or returning more than the eligible balance fails. |
| FAB-05 | Duplicate submission with the same idempotency key creates one transaction. |
| FAB-06 | A cutting session draws from two batches and outputs two sizes; allocations reconcile to batch consumption and approved waste. |
| FAB-07 | Posted movements cannot be silently edited/deleted; an authorized reversal preserves the original and restores correct balances. |
| FAB-08 | Metres and yards cannot be combined without an explicit supported conversion. |
| COST-01 | Fabric still held in cutting is not labelled consumed cost. Labor is not counted twice through invoice/payment entries. |
| DATA-01 | Exported records persist after reload and are visible from a second authorized device. |
| DATA-02 | Thai names, punctuation and `+` characters do not corrupt keys, searches or joins. |
| MIG-01 | Dry-run import changes no business records. Rerunning a completed import creates no duplicates. |
| MIG-02 | Orphaned IDs, invalid values and missing historical batches appear in a reviewed exception report. |
| OPS-01 | A backup can be restored into a separate test environment and reconciles against the source backup. |

Use meaningful integration tests against a test database for stock posting, concurrency, payments and permissions. UI tests should cover the main user journeys and validation failures. Test data must be synthetic and isolated from production.

## 12. Delivery sequence and definition of done

1. **Design:** requirements matrix, ERD, permissions, decisions and architecture/deployment plan.
2. **Foundation:** repository, local Docker environment, PostgreSQL schema/migrations, authentication, roles, master data and audit foundation.
3. **Core workflow:** PO/PR lines, batch receipts, issues, cutting/returns, stock/cost reports with transaction tests.
4. **Operations:** assignments, partial QC, wages/invoices, payments, cost templates and document output.
5. **Migration:** staging/import tools, exceptions, reconciliation and opening-balance/cutover plan.
6. **Deployment:** CI/CD, AWS configuration, backups/restore verification, monitoring and user guide.

For each stage, supply a working result and identify passed tests, missing items and blocked decisions. Include README, schema migrations, `.env.example` with names only, local startup steps, test commands, deployment guide and backup/restore steps. Do not claim production readiness or complete folder replacement until the relevant acceptance tests and migration reconciliation pass.

## 13. Decisions to confirm before financial cutover

Proceed with independent implementation while these are resolved:

1. Does “batch” mean supplier dye-lot, receipt-cost batch, individual roll or cutting session? Proposed model separates them.
2. Must rolls/remnants be tracked individually? Which quantity units occur in real operations?
3. Are Papradit and GPT legally separate companies? Which users may see cross-company costs/prices?
4. What do the two PPD-to-GPT price fields mean, and what is the VAT/tax convention?
5. Who approves POs, QC, wage invoices, payments and stock adjustments? Is self-approval allowed?
6. Are wages payable on assigned, received or QC-accepted quantities? How are rejects/rework handled?
7. How should shared fabric consumption/waste and fixed overhead be allocated to jobs/sizes?
8. Will migration include full history or active records plus opening balances? What is the cutover date?
9. Which user login method is preferred for staff, and what email addresses/roles should be invited?

## Appendix: observed source references

These are provenance links, not a requirement for Codex to access Drive:

- Papradit_DB: https://drive.google.com/drive/folders/1zwBy11gLJjYIHe4Jqm3zPLqRrxM8hYjB
- GPT_DB: https://drive.google.com/drive/folders/1K0VZ3WqICsd0BqkX7uNGWVToLQSPqW4e
- รับจ่ายงาน: https://docs.google.com/spreadsheets/d/1uZS2F7_bk95mY62-1uwGeQK2Fd2Sr6CPFzoA2BH7lP0/edit?usp=drivesdk
- ClothingModel: https://docs.google.com/spreadsheets/d/13KtNcOjdB_DP-grJe8SgvFwNxYod02Op38fnqSTMO4I/edit?usp=drivesdk
- จ่ายค่าแรง: https://docs.google.com/spreadsheets/d/1IWhPE9zf08nM8Lhm0H2em3-ZzvjUk5I8uuOhSXImtFE/edit?usp=drivesdk
- งานและสินค้า: https://docs.google.com/spreadsheets/d/1WqS5TR2wl9E8CzHvfj6w95U2oaYSMqJiM-Gx_peOYhI/edit?usp=drivesdk
- PO_Approval: https://docs.google.com/spreadsheets/d/1Kpxq4u5vCcPCk_uEM6nENItroP1afRmMr5X7waWWTM0/edit?usp=drivesdk
- ต้นทุนผ้า: https://docs.google.com/spreadsheets/d/1GHVU-NTugdbMYawMr8BLq6iDwb4KZ0MiGG5UkXTsvCQ/edit?usp=drivesdk
