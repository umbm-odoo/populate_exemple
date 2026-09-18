# Populate Demo — Wingardium Odoosa BI talk

Generates a historically-realistic transactional dataset for the BI talk
(spec: `../Odoo_BI_Data_Spec_v2.md`). This module contains no data of its
own beyond the Populate blueprints (`populate/fixture.xml`,
`populate/pilot.xml`) and the code that drives them — the master data
(customers, products, warehouses, suppliers, BOMs, ...) is **not** part of
this module and has to be imported separately before either blueprint can
run, because both reference it by external ID (`__import__.<xmlid>`).

This is **not** a released Odoo version — "19.5" is `odoo/odoo`'s
`master` branch, which moves daily and makes breaking schema changes
(e.g. `stock.valuation.layer` doesn't exist on this snapshot; it was
replaced by `value`/`remaining_qty`/`remaining_value` fields directly on
`stock.move`). Running this against any released version (18.0, a stable
19.0 once it exists, Odoo.sh's stable branches, ...) - or even a
*different* master snapshot - will fail with tracebacks that look like
missing fields/models, because the schema genuinely is different. This is
also almost certainly why restoring a dump taken from this module
elsewhere fails: the target database needs to be running these same
commits, not just "some 19.x build".

Pin to:
- `odoo/odoo` core: commit `f63f1cca433b182d003f0ac4eb9f8e2efaad810d` (2026-08-25)
- `odoo/enterprise`: commit `b8b09590ddb5a88f30fdd5249f4c830002abdc64` (2026-08-25)

## Project layout

Everything needed to reproduce the dataset from scratch on another machine
lives in this repo — nothing depends on state that only exists on one
laptop.

```
populate_demo/
  __manifest__.py, __init__.py       module registration
  models/                            historical-date-aware wrappers around
                                      native Odoo actions (confirm, produce,
                                      validate, post, pay, ...) - see each
                                      file's docstring for what it corrects
                                      and why
  generators.py                      custom Populate generators that feed
                                      populate/data/pilot_plan.json's rows
                                      to the blueprint one record at a time
  planner/                           pure-Python plan generation - no Odoo
                                      dependency, unit-testable on its own
    config.py                        *every* tunable number, weight, date
                                      range, and master-data xmlid
                                      reference - see "Configuration" below
    quotas.py, regions.py, crm.py,   the algorithms that turn config.py's
    outstanding.py, eligibility.py,  data into quota tables, eligibility
    parties.py, seasonal.py,         pools, schedules, and baskets - no
    basket.py, pricing.py,           tunable data of their own, only logic
    attribution.py, schedule.py,
    rounding.py
    plan.py                          orchestrates all of the above into one
                                      order-by-order plan
    dump_plan.py                     authoring tool: plan.py -> pilot_plan.json
    gen_pilot_blueprint.py           authoring tool: pilot_plan.json -> pilot.xml
    import_master_data.py            authoring tool: workbook -> Odoo master data
    data/snapshot.json               committed: customer/supplier eligibility
                                      snapshot (planner input)
  populate/
    fixture.xml                      13-order hand-picked edge-case blueprint
    pilot.xml                        generated: the 1,000-order pilot blueprint
    data/pilot_plan.json             generated: the plan pilot.xml reads
```

`Odoo_BI_Data_Spec_v2.md` and the source workbook
(`[RNG][OXP2026] Talk data _ Heavyweight DB.xlsx`) live one level up, next
to `populate_demo/`, and are committed in the same repo.

## Configuration

**Every** tunable number lives in exactly one file: `planner/config.py`.
Region/family/basket weights, quantity ranges, discount rates, CRM link and
cancellation rates, lead times, payment terms, loss-reason and
attribution-source weights, warehouse opening dates, price factors, product
xmlid references - all of it, with a comment tying each block back to the
spec section it implements. Nothing else defines this data locally; every
other `planner/*.py` module only imports from `config.py` and contains
algorithms, not numbers.

To change a distribution, a rate, a lead time, or which xmlid a
family/team/source maps to: edit `config.py` only, then regenerate (see
step 3 below). The one exception is genuinely new master data (e.g. a 17th
product) - that also needs a `planner/data/snapshot.json` re-export and,
for a new sellable product, a `PRODUCT_2026_LIST_PRICE` entry.

## 0. Set up Odoo itself (no `odev`)

These steps assume plain Odoo tooling, not the `odev` CLI.

```bash
git clone git@github.com:odoo/odoo && (cd odoo && git checkout f63f1cca433b182d003f0ac4eb9f8e2efaad810d)
git clone git@github.com:odoo/enterprise && (cd enterprise && git checkout b8b09590ddb5a88f30fdd5249f4c830002abdc64)

python3 -m venv odoo-venv
odoo-venv/bin/pip install -r odoo/requirements.txt
odoo-venv/bin/pip install openpyxl   # needed for the master-data import script in step 2

# Adjust to wherever you cloned/put things - reused in every command below.
ODOO_BIN=$(pwd)/odoo/odoo-bin
PYTHON=$(pwd)/odoo-venv/bin/python
ADDONS_PATH=$(pwd)/enterprise,$(pwd)/odoo/addons,/path/to/custom_addons
```

`custom_addons` above is this repo's clone location (the parent directory
of `populate_demo/`) - not `populate_demo/` itself. Postgres needs to be
running locally with passwordless access for the OS user running these
commands (the usual local-dev setup); `createdb`/`dropdb` below are plain
`postgresql-client` commands, nothing Odoo- or odev-specific.

## 1. Create a fresh database and install the module

```bash
dropdb --if-exists <dbname> && createdb <dbname>
$PYTHON $ODOO_BIN --addons-path=$ADDONS_PATH -d <dbname> \
  -i populate_demo --stop-after-init
```

## 2. Import the master data

Source file: `../[RNG][OXP2026] Talk data _ Heavyweight DB.xlsx` — one sheet
per model, 26 sheets, **in the exact order they appear in the workbook**
(that order is already a valid dependency order: companies before
warehouses, products before supplierinfo/BOMs, analytic plans before
analytic accounts before budget lines, etc.). Each sheet's `id` column is a
*bare* external ID (no module prefix) — loading it via `load()` puts it
under Odoo's `__import__` pseudo-module, which is why every blueprint
reference reads `env.ref('__import__.' + name)` rather than
`env.ref('populate_demo.' + name)`.

The import script (`planner/import_master_data.py`) handles two workbook
quirks that would otherwise break `load()` (a legacy location-naming
reference, and one model name Excel's 31-character sheet-name limit
truncated) and one Odoo quirk: `budget.line` uses fields (`x_plan2_id`,
`x_plan3_id`) generated by `analytic.plan.fields.mixin` from however many
`account.analytic.plan` records exist, and that field generation only
happens at registry load time - importing the plans and loading
`budget.line` in the *same* process fails with `Invalid field name
'x_plan3_id'` even though the plans are already committed. The script
therefore **runs in two passes with a process restart in between**:

```bash
MASTER_DATA_XLSX="/path/to/custom_addons/[RNG][OXP2026] Talk data _ Heavyweight DB.xlsx" \
  $PYTHON $ODOO_BIN shell --addons-path=$ADDONS_PATH -d <dbname> --no-http \
  < planner/import_master_data.py

# restart the shell, then:
IMPORT_RESUME_AFTER=account.analytic.plan \
MASTER_DATA_XLSX="/path/to/custom_addons/[RNG][OXP2026] Talk data _ Heavyweight DB.xlsx" \
  $PYTHON $ODOO_BIN shell --addons-path=$ADDONS_PATH -d <dbname> --no-http \
  < planner/import_master_data.py
```

Verified working end to end against a fresh database — e.g.
`env.ref('__import__.prod_felix')` should resolve after both passes.

## 3. Generate the pilot plan and blueprint

The 1,000-order "1% pilot" blueprint (`populate/pilot.xml`) and the plan it
reads (`populate/data/pilot_plan.json`) are both generated, committed
artifacts — `planner/dump_plan.py` and `planner/gen_pilot_blueprint.py` are
authoring tools, not run by Odoo. Only re-run them if you're changing
`config.py`, the seed, or the scale; the committed files already match
what's described in the spec.

```bash
cd populate_demo
python3 planner/dump_plan.py            # writes populate/data/pilot_plan.json
python3 planner/gen_pilot_blueprint.py   # writes populate/pilot.xml
```

Both scripts read `PILOT_SCALE` / `PILOT_SEED` env vars (default `0.01` /
`20260920`, the real 1,000-order pilot; `1.0` is the spec's full
100,000-order target - "the agreed 100,000-order dataset is a 100× run").
For a fast local iteration cycle while debugging, `PILOT_SCALE=0.002` gives
~200 orders and still exercises every outcome/sub-bucket. Not every scale
value is valid - every quota table (annual/outcome, outstanding sub-bucket,
and the three extra CRM volumes) has to divide evenly at once; the script
raises `ValueError` naming which one failed if it doesn't - try a nearby
value (multiples of `0.0005` satisfy the CRM tables; combined with the
other tables, `0.002`/`0.005`/`0.01`/`0.02`/.../`1.0` are all confirmed
good).

If you touch the planner, regenerate both files together — `pilot.xml` is
derived from `pilot_plan.json`, they must be regenerated as a pair.

## 4. Run the blueprint

```bash
$PYTHON $ODOO_BIN populate --addons-path=$ADDONS_PATH -d <dbname> \
  -b populate_demo.blueprint_pilot --seed 20260920
```

Use `populate_demo.blueprint_fixture` instead for the small 13-order
hand-picked fixture (spec §15) covering every workflow edge case.

**Never re-run `odoo-bin populate` on a database an earlier attempt already
partially populated** — it always starts a brand-new session and replays
every block in the blueprint from the top, so a retry after a failure
duplicates everything the first attempt already committed. Drop and
recreate the database (step 1) before every retry.

At 1,000 orders this takes roughly 35-50 minutes depending on machine load
— most of it is real Odoo business logic (`action_confirm`,
`button_validate`, `button_mark_done`, ...) replayed order by order, not
bulk inserts, so it doesn't parallelize trivially.

## Status against the spec

Implemented and verified: annual/geographic quotas, CRM linkage (70,000
linked + the 50,000 unlinked lost/open/unconverted records, 120,000
total), customer/supplier eligibility and phasing, warehouse routing and
opening dates, historical date sequencing, basket composition including
the Chocogrenouilles spike and campaign link, year-specific selling/vendor
price factors, line discounts, vendor bills and payments, and a run
manifest (pinned commits/seed/scale saved with each generated plan).

Not yet built: the transit-valuation report (spec §6's allocated-FIFO-
in-transit calculation - a standalone report, not a blueprint change), and
automated §14 validation/performance-benchmark checks. The full
100,000-order run (`PILOT_SCALE=1.0`) has not yet been executed end-to-end
in Odoo - only plan generation has been verified at that scale; expect
further scale-dependent issues the same way the pilot did going from
120→500→1,000 orders.
