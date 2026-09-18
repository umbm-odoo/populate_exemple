**Odoo BI demo data specification**  
Version 2 — 17 September 2026  
   
 Business: Wingardium Odoosa  
   
 Target: Odoo Enterprise on master, using Populate  
   
 Scenario period: 1 January 2016 through 20 September 2026  
**1. Purpose and status**  
Create a coherent operational database for a talk about designing BI reports and managing reporting performance. The audience must be able to follow demand from CRM through sales, purchasing, manufacturing, international fulfilment, invoicing, and accounting. Reports should reveal growth, seasonality, geographic expansion, commercial conversion, outstanding work, and inventory in transit.  
This specification defines transactional generation for the first Populate blueprint attempt. Existing master data is an input. The user maintains and imports it separately; the blueprint must not recreate, delete, retag, or reprice those master records. It does not claim that an executable blueprint or live database has been validated. The supplied workbook and XML were inspected; the local Odoo database and Enterprise source were not available. Public Community master source was consulted. Pin both Community and Enterprise revisions before implementation.  
**Confirmed decisions** are the scenario dates, 100,000 sales-order records, the outcome mix below, 70% CRM linkage, the three destination regions, 60% UK share within Europe, cohort sizes, four warehouses, central Belgian supply, dedicated transit locations, EUR, FIFO, and retention of the existing Server Action. Detailed weights, delays, prices, and generation mechanics below are  **proposed v1 defaults**, made explicit so the first attempt can be implemented and reviewed.  
The cutoff is a fixed synthetic reporting date, including 20 September in Europe/Brussels time. It is deliberately later than the preparation date. Never use the execution date or relative expressions such as today -10y as the historical anchor.  
**2. Reporting stories**  
| | | |  
|-|-|-|  
| **Story** | **Data mechanism** | **Demonstration** |   
| Growth after Covid | Modest growth before 2020, a 2020 dip, a step up in 2021, then expansion | Separate order-count growth from price, basket, and product-mix effects |   
| Back to school | Repeated August and September demand peaks | Compare the same calendar windows across years |   
| International expansion | Americas and Asia-Pacific gain share; regional warehouses open in 2021 | Separate destination region from fulfilment warehouse |   
| A recognisable exception | A short Chocogrenouilles / Chocolate Frogs surge in November 2020 | Drill from an outlier to products, campaign, orders, and invoices |   
| Conversion does not equal revenue | Lost opportunities, cancelled quotations, cancelled confirmed sales, and open work | Distinguish won CRM value, confirmed orders, deliveries, invoicing, and cash |   
| Goods travelling between warehouses | Belgian dispatch and regional receipt occur on different dates | Show quantity, age, expected arrival, and allocated FIFO book value in transit |   
| Reporting performance | Several hundred thousand lines and linked operational records | Demonstrate row multiplication, selective filters, aggregation grain, and measured query cost |   
   
Marketing sources support attribution and conversion analysis. Do not call an attribution chart “marketing ROI” without generating corresponding marketing spend; spend is outside v1.  
**3. Volumes and outcomes**  
The 100,000 records are sale.order records, including quotations and cancellations. This is the full target dataset, not 100,000 confirmed sales plus exceptions.  
| | | |  
|-|-|-|  
| **State at the cutoff** | **Count** | **Required downstream state** |   
| Delivered and invoiced | 83,000 | Confirmed sale, completed customer delivery, posted customer invoice |   
| Confirmed awaiting fulfilment | 2,000 | Open operational demand; no customer delivery or customer invoice yet |   
| Cancelled | 10,000 | Cancelled sale/quotation; no completed customer delivery or customer invoice |   
| Open quotation | 5,000 | Draft or sent quotation; no procurement, delivery, or invoice |   
| **Total** | **100,000** |   |   
   
Defaults for the 10,000 cancellations: 8,000 quotations cancelled before confirmation and 2,000 confirmed orders cancelled before physical procurement/production begins. Cancel their dependent outstanding demand. This avoids needing returns and credit notes in the first attempt. Do not cancel completed stock moves or posted invoices to simulate this population.  
Defaults for the 2,000 outstanding confirmed orders: 1,000 have finished goods in transit to regional warehouses, 600 await production in Belgium, and 400 await purchased goods/components. These are order counts, not picking, purchase-order, or manufacturing-order counts. Consolidation means the latter counts will differ. All outstanding orders are recent 2026 orders.  
For sales lines, allocate order line counts with weights: 1 line 10%, 2 lines 20%, 3 lines 30%, 4 lines 20%, 5 lines 15%, 6 lines 5%. Applying these exact quotas gives **325,000 sales lines**. Every order has at least one line. Use distinct products within an order and integer unit quantities.  
Generate one customer invoice per completed sales order, yielding **83,000 customer invoices** in v1. The invoice's commercial lines correspond to the delivered sales lines. Accounting journal items also include receivable and tax lines, and are not equal in count to invoice product lines.  
Purchases, receipts, manufacturing orders, internal transfers, vendor bills, payments, analytic entries, and journal items are derived from demand and workflow. Do not impose independent counts such as the old XML's 60,000 purchase orders or the old document's 100,000 total accounting entries. Measure their actual counts after the pilot.  
**Annual allocation**  
These are proposed exact quotas, grouped by quotation/order creation year. Confirmation, delivery, invoice, and payment year can differ near a year boundary.  
| | | | | | |  
|-|-|-|-|-|-|  
| **Year** | **All SO records** | **Delivered and invoiced** | **Awaiting fulfilment** | **Cancelled** | **Open quotations** |   
| 2016 | 1,500 | 1,300 | 0 | 200 | 0 |   
| 2017 | 1,900 | 1,650 | 0 | 250 | 0 |   
| 2018 | 2,400 | 2,100 | 0 | 300 | 0 |   
| 2019 | 3,000 | 2,650 | 0 | 350 | 0 |   
| 2020 | 2,700 | 2,300 | 0 | 400 | 0 |   
| 2021 | 8,000 | 7,100 | 0 | 900 | 0 |   
| 2022 | 11,000 | 9,850 | 0 | 1,150 | 0 |   
| 2023 | 12,500 | 11,000 | 0 | 1,500 | 0 |   
| 2024 | 14,500 | 13,100 | 0 | 1,400 | 0 |   
| 2025 | 18,000 | 16,450 | 0 | 1,550 | 0 |   
| 2026 to 20 September | 24,500 | 15,500 | 2,000 | 2,000 | 5,000 |   
| **Total** | **100,000** | **83,000** | **2,000** | **10,000** | **5,000** |   
   
Recent pipeline is intentionally substantial for the demonstration. Keep open quotations within the last 60 days of the scenario and outstanding confirmed orders within the last 45 days. Allocate these groups separately so they do not distort the seasonal distribution of completed business.  
**4. Customer and supplier cohorts**  
Use the existing 150 customers and 25 suppliers, with the agreed **30 Phase 1 / 120 Phase 2** customer split and  **10 Phase 1 / 15 Phase 2** supplier split. Resolve their existing external IDs and tags. If the imported master data does not match these populations, report the discrepancy rather than modifying it.  
Phase 1 is eligible from 1 January 2016. Phase 2 cannot participate before 1 January 2021. Earlier customers and suppliers remain eligible after expansion; Phase 2 adds to the population rather than replacing Phase 1.  
Proposed customer onboarding: 40 in 2021, 24 in 2022, 20 in 2023, 16 in 2024, 12 in 2025, and 8 in 2026. Use 1 January as the eligibility date for each annual cohort. All 15 additional suppliers are eligible from 1 January 2021. The spec's eligibility dates are generation controls, not invented standard Odoo fields.  
Create a persistent external-ID-to-eligibility mapping for the generator. Preserve names and countries. Choose Phase 1 customers with representation in every active destination bucket: 14 UK, 10 other Europe, 4 Americas, and 2 Asia-Pacific. Choose suppliers by the products they can supply, ensuring an eligible pre-2021 vendor exists for every purchased item and component.  
Select customers by destination bucket first, then by eligible customer within that bucket. Customer counts do not determine transaction shares. Preserve existing customers outside the three destination regions, but exclude them from generated sales. Supplier countries may remain global.  
No CRM creation, quotation, purchase, receipt, or other activity may predate the participating customer's or supplier's eligibility. Eligibility is also checked when old customers place repeat orders.  
**5. Geographic distribution**  
Weights apply to **confirmed sales-order counts**, including the 2,000 orders still awaiting fulfilment. Cancelled and open records use the same year's weights as a sampling default. Use shipping destination rather than invoicing address for this analysis.  
| | | | | |  
|-|-|-|-|-|  
| **Year** | **Europe** | **Americas** | **Asia-Pacific** | **UK share within Europe** |   
| 2016–2020 | 80% | 15% | 5% | 60% |   
| 2021 | 70% | 20% | 10% | 60% |   
| 2022 | 66% | 22% | 12% | 60% |   
| 2023 | 62% | 24% | 14% | 60% |   
| 2024 | 58% | 26% | 16% | 60% |   
| 2025 | 54% | 28% | 18% | 60% |   
| 2026 | 50% | 30% | 20% | 60% |   
   
For example, the UK receives 30% of all confirmed orders in 2026: 50% × 60%. Allocate whole-record quotas with largest-remainder rounding and deterministic tie-breaking. Reconcile within one order of the mathematical target at each annual geographic level.  
Define the region mapping explicitly from the countries present in the workbook. Keep UK separate within Europe; include Australia in Asia-Pacific and North/South America in Americas. Do not silently assign African countries to Europe. An unmapped sales country is a validation error.  
**6. Warehouses and transit**  
Use one Belgian legal company and EUR throughout. Warehouse country is a logistics dimension; it does not create additional legal entities or intercompany sales.  
| | | | | |  
|-|-|-|-|-|  
| **Warehouse** | **Code** | **Business role** | **Operational from** | **Typical transit from Belgium** |   
| Belgium Hub | BE | Central purchasing and manufacturing; continental European fulfilment | 2016-01-01 | Not applicable |   
| UK Distribution | UK | UK customer deliveries | 2016-01-01 | 2–5 days |   
| US Distribution | US | Americas customer deliveries | 2021-01-01 | 8–16 days |   
| Singapore Distribution | SG | Asia-Pacific customer deliveries | 2021-01-01 | 12–22 days |   
   
Before 2021, Belgium delivers directly to the Americas and Asia-Pacific. Warehouse opening dates constrain all associated stock operations, not just sales-order selection.  
Use the four existing destination-specific locations of type transit: **Transit to BE**,  **Transit to UK**,  **Transit to US**, and  **Transit to SG**, belonging to the Belgian company. Transit to BE is reserved for future return/rebalancing flows and may have zero balance in v1; do not manufacture activity simply to populate it.  
The core physical sequence is:  
Vendor → BE Stock → Transit to destination → Regional Stock → Customer  
For manufactured products, purchased components first feed Belgian production, which supplies finished goods to BE Stock. Each regional replenishment has a Belgian dispatch and a separate regional receipt. The dispatch may be done while the receipt remains waiting. Completing the dispatch must never automatically complete the arrival.  
Use simple one-step warehouse receipts and deliveries. Interwarehouse transit supplies the two distinct events needed for this talk; extra packing or quality-control steps are not needed.  
**Transit reporting and value**  
At reporting instant T, transit quantity is the cumulative completed quantity entering the selected transit location through T minus completed quantity leaving it through T. Waiting moves are expected activity, not realised inventory. Historical reports must reconstruct balances from dated completed moves; today's stock.quant balance alone cannot answer a historical question.  
Use FIFO for company inventory accounting. For the first reporting implementation, define **allocated FIFO book value in transit** as:  
Transit quantity for company/product at T × company FIFO inventory value at T ÷ total company-owned inventory quantity for that product at T  
Calculate per product in its stock unit, then aggregate in EUR. A zero quantity denominator with nonzero value is an exception to investigate, not a reason to substitute today's cost. Include all valued internal and company-owned transit inventory in the reconciliation denominator.  
This definition is an allocation of company FIFO book value, not a claim that Odoo stores a separate acquisition-cost layer for each transit location. The inspected master valuation code can allocate company value proportionally when restricting warehouse quantities. Verify the installed revision and reconcile the report to it before claiming native equivalence. Exact shipment acquisition-cost tracing would require an additional movement/cost allocation ledger and is outside the first reporting definition. Internal transfers do not generate revenue or vendor/customer bills. [S2]  
Report dispatch date, expected receipt date, actual receipt date when present, days in transit, quantity, and allocated FIFO book value. Demonstrate both historical month-end balances and the positive cutoff balance from the 1,000 in-transit orders.  
**7. Products, prices, and seasonality**  
Use the existing catalogue and product IDs, including **Chocogrenouilles (Chocolate Frogs)**. Manufacture both wands and both potions in Belgium; purchase brooms and consumables for resale. Purchase all manufacturing components into Belgium.  
The transaction scenario expects 16 products, four BoMs, and eight BoM lines, including an Elder Wood Wand BoM with one Elder Wood Branch and one Thestral Tail Hair. Read recipes from the existing BoMs; do not generate master recipes in Populate.  
Proposed 2026 net selling prices in EUR:  
| | | |  
|-|-|-|  
| **Product** | **Unit price** | **Supply** |   
| Holly & Phoenix Feather Wand | 135.00 | Manufacture |   
| Elder Wood Wand | 360.00 | Manufacture |   
| Nimbus 2000 | 280.00 | Purchase |   
| Firebolt | 675.00 | Purchase |   
| Felix Felicis | 210.00 | Manufacture |   
| Polyjuice Potion | 165.00 | Manufacture |   
| Chocogrenouilles | 7.50 | Purchase |   
| Gillyweed | 26.00 | Purchase |   
   
Use the workbook's purchased-item standard costs as initial 2026 vendor-price anchors. New Elder Wood and Thestral Hair anchors are EUR 60 and EUR 90. Manufactured costs must come from actual component consumption and the configured production valuation, rather than independent random costs. Default v1 has no work-centre labour or overhead absorption, no scrap, and no landed costs.  
Use the existing supplier price records, with an eligible early supplier and at least one alternative for each purchased product. The business chooses among eligible suppliers using weights 70% primary / 30% alternative; it must not reference a Phase 2 supplier before 2021. Centralise all supplier receipts in Belgium.  
For historical commercial amounts, use year-specific price factors instead of applying current prices to old transactions:  
| | | |  
|-|-|-|  
| **Year** | **Selling-price factor** | **Vendor-cost factor** |   
| 2016 | 0.78 | 0.72 |   
| 2017 | 0.80 | 0.74 |   
| 2018 | 0.82 | 0.76 |   
| 2019 | 0.85 | 0.79 |   
| 2020 | 0.85 | 0.80 |   
| 2021 | 0.88 | 0.84 |   
| 2022 | 0.92 | 0.94 |   
| 2023 | 0.95 | 0.97 |   
| 2024 | 0.97 | 0.98 |   
| 2025 | 0.99 | 0.99 |   
| 2026 | 1.00 | 1.00 |   
   
Apply selling factors at quotation date and vendor factors at purchase confirmation. Lock the resulting line prices into downstream invoices and bills. Round unit prices to currency precision. These factors intentionally permit a 2022 margin squeeze.  
Default product-family weights for sales lines are 20% wands, 25% brooms, 30% potions, and 25% consumables. Choose equally between the two products within each family except during the anomaly. Treat these as statistical targets, not exact quotas, because baskets cannot repeat a product.  
Default corporate order share is 20% within each destination bucket where both customer types exist; the number of corporate contacts does not imply their order share. Use individual quantities of 1–2 wands, 1 broom, 1–3 potions, and 2–8 consumables. Corporate quantities are 3–8 wands, 1–3 brooms, 5–15 potions, and 20–60 consumables. Sample integer quantities uniformly within those ranges. Use 0% discount for individuals and 5% for corporate orders.  
**Repeating calendar pattern**  
For completed and cancelled business, sample the lead product family first, then choose quotation dates with the following daily weights. Remaining basket lines follow the family mix. Hold annual order quotas fixed and normalise the daily weights over the permitted dates.  
| | | | |  
|-|-|-|-|  
| **Period each year** | **Wands and brooms** | **Consumables** | **Potions** |   
| Most of the year | 1.0 | 1.0 | 1.0 |   
| 1–31 August | 2.5 | 3.0 | 1.5 |   
| 1–20 September | 3.0 | 4.0 | 1.5 |   
| 21–30 September | 1.5 | 1.5 | 1.0 |   
   
Customer deliveries and invoices follow their actual lags; their peaks need not occur on exactly the same day as quotations. Backward-schedule upstream supply so the completed 2026 population includes feasible deliveries and invoices through 20 September. Draw the outstanding population separately.  
For 1–14 November 2020, multiply Chocogrenouilles quantities by four on orders containing that product and assign the special campaign. Keep overall 2020 order counts unchanged. This makes the exception distinguishable from the recurring school-season peak. Apply the resulting extra demand to purchases, stock, invoices, and analytics as well.  
Compare 1–20 September 2026 with 1–20 September in prior years. Show year-to-date comparisons through 20 September separately from complete-year figures.  
**8. CRM and commercial consistency**  
Link exactly **70,000 orders** to CRM opportunities: 58,100 completed, 1,400 awaiting fulfilment, 7,000 cancelled, and 3,500 open quotations. The remaining 30,000 orders are direct/repeat orders without a CRM opportunity. For v1, use one opportunity per linked order; do not randomly reuse an opportunity across unrelated customers.  
Proposed CRM total is **120,000 records**: the 70,000 linked opportunities, 40,000 lost opportunities without a quotation, 6,000 recent open opportunities without a quotation, and 4,000 recent unconverted leads. These additional volumes are defaults rather than previously agreed quotas.  
Use stages New, Qualified, Proposal, Negotiation, and Won, with native lost-state handling and a loss reason. Loss reasons use weights Price 40%, Timing 25%, Competitor 25%, and No need 10%. Set stage, active/lost behaviour, probability, and closure date consistently through supported workflow methods; probability alone does not constitute a valid lifecycle.  
An opportunity becomes won when its order is confirmed. Thus 1,400 CRM-linked orders that were confirmed and later cancelled remain evidence of an initial win followed by a commercial cancellation. The other 5,600 linked cancellations are lost quotations. This produces 60,900 won opportunities, 45,600 lost opportunities, 9,500 open opportunities, and 4,000 unconverted leads.  
For linked records, customer, company, salesperson, sales team, campaign/source attribution, and currency must agree. Expected revenue is the quotation net amount once a quotation exists; lost opportunities without quotations can carry an independently estimated potential amount. Do not equate expected revenue with accounting revenue.  
Use the four existing house teams, four managers, and twelve sales representatives. Assign each order to one of the twelve representatives and derive its team from membership. Do not sample arbitrary internal users, administrators, or managers as representatives.  
Use Daily Prophet / Gazette du Sorcier, Owl Post / Courrier hibou, referrals, and online shop sources. Defaults before 2021 are 45% / 25% / 20% / 10%; from 2021 they are 20% / 25% / 20% / 35%. Match medium to source. Store the opportunity's selected attribution on the linked order rather than drawing it again.  
**9. Demand-driven purchasing and manufacturing**  
Sales demand is the root of the supply calculation. Open quotations create no stock demand. Confirmed demand determines finished-product requirements at each warehouse, central replenishment requirements, manufacturing quantities, component requirements, and vendor purchases.  
Use native sales, stock, purchase, and manufacturing workflows. Use the existing Buy and Manufacture routes at Belgium and regional resupply through the dedicated transit locations. Route selection must distinguish purchased resale products from manufactured finished goods and must not cause both purchase and manufacture for the same requirement.  
Default consolidation is by company, week, vendor, and receiving warehouse for purchases, and by company, week, product/BoM, and manufacturing warehouse for production. Quantities equal allocated demand less available uncommitted stock. Keep an allocation mapping from each consolidated supply line/batch back to the sales demand it covers; an origin text string alone is insufficient for reliable many-to-many reporting.  
Do not assume standard route execution will automatically achieve those exact weekly groupings. The blueprint helper must either consolidate supported procurements before workflow creation or explicitly record the actual native grouping. Validate the chosen approach in the pilot; never create independent duplicate POs/MOs alongside an already-triggered native supply chain.  
Manufacturing must consume the actual BoM components, finish the required output quantity, and make it available before the outbound dispatch. Zero opening stock is the v1 default. Generate the initial vendor receipts early enough to support the first completed sales, rather than manufacturing negative-stock inventory.  
Simple lead-time defaults are 5–12 days from purchase confirmation to vendor receipt and 1–4 days for production after all required components are available. Customer delivery after available stock is 1–3 days in Europe and 2–5 days from regional warehouses in the Americas/Asia-Pacific. Direct Belgian deliveries to those regions before 2021 use 8–16 and 12–22 days respectively. Internal-transfer travel times are in section 6.  
For 10% of completed customer deliveries, add a 2–5 day delay beyond the original promised date. Retain both promised and actual dates. Sample only feasible timelines within the scenario rather than clipping dates to the cutoff.  
**10. Historical date contract**  
Generate a complete event schedule before writing transaction records. Draw durations from the ranges above, then derive related dates. Never independently sample dates for leads, orders, receipts, deliveries, and invoices.  
| | |  
|-|-|  
| **Event** | **Dating rule** |   
| Lead/opportunity creation | On or after customer eligibility and scenario start |   
| Quotation creation | Lead creation plus 1–14 days when CRM-linked |   
| Sales confirmation | Quotation creation plus 1–10 days |   
| Opportunity won date | Sales confirmation date for linked confirmed orders |   
| Lost quotation closure | On or after quotation creation, with no confirmation |   
| Purchase request/confirmation | On or after the demand event that causes it; confirmation within 0–2 days of request |   
| Vendor receipt | After purchase confirmation and supplier lead time |   
| Manufacturing start | After all consumed components are available |   
| Manufacturing finish | On or after start, before finished-goods dispatch |   
| Belgian dispatch | After sale confirmation and required goods are available |   
| Regional receipt | After dispatch plus actual transit duration |   
| Customer delivery | After the fulfilling warehouse has received/produced the goods |   
| Customer invoice | Delivery date or up to 2 days later; posted by cutoff for completed cohort |   
| Vendor bill | Supplier receipt date or up to 5 days later, subject to cutoff |   
| Payment | On or after the associated invoice/bill accounting date |   
   
For consolidated procurement, request creation follows the earliest allocated confirmed demand; delivery availability must still satisfy every allocated sale. Future scheduled dates are allowed on open work. Future **actual** completion, posting, or payment events are not.  
Use local business dates in Europe/Brussels and store datetimes in UTC. The reporting cutoff is exclusive 2026-09-21 00:00:00 Europe/Brussels. Date fields such as invoice and accounting dates remain calendar dates.  
The implementation must inspect and align relevant fields on the pinned revision: quotation create_date, sales date_order after confirmation, promise/commitment dates, CRM closing dates, purchase approval/planning dates, stock picking completion and schedule dates, stock move and move-line dates, manufacturing start/finish fields, invoice date, accounting date, due date, and payment date. Store the original quotation timestamp separately in the generation event map if confirmation overwrites its business date.  
Audit timestamps are a separate concern from business dates. Generated transaction create_date values must represent historical record creation; line records cannot precede their parent. If historical write_date is simulated, it must not precede creation or the last simulated event. Do not alter unrelated/master records simply to make audit dates uniform.  
Native methods may stamp the current execution date. The first pilot must establish which methods accept historical values or context, which dates they overwrite, and whether a controlled correction is needed. A context key must not be assumed to freeze time merely because its name sounds appropriate.  
If corrections require SQL, scope them to generated record IDs from the run manifest, use parameterised statements, invalidate/recompute dependent values as required, and rerun chronological valuation/accounting checks. Never shift only date_order, date_done, or create_date while leaving linked stock and accounting dates unchanged. FIFO must be computed using the intended historical chronology; moving dates afterward without recomputing valuation is not sufficient.  
**11. Accounting, payments, and analytics**  
Use the existing Belgian company's accounting environment and EUR journals. Validate that the existing chart, journals, receivable/payable, stock valuation/variation, revenue, expense, and outstanding payment accounts support posting; report missing prerequisites without creating them. The demo includes operational accounting, not payroll, financing, fixed assets, or a fully modelled statutory balance sheet.  
Use delivery-based sales invoicing and receipt-based vendor billing for v1. Customer invoices retain sale-line links; vendor bill lines retain purchase-line links. Post balanced accounting entries through native methods. Do not create invoices/bills independently and attempt to reconnect them afterward.  
Apply the existing taxes and fiscal-position mappings from the installed localisation. Preserve geographic and customer-type distinctions, but do not invent a universal international VAT rate. Revenue and margin reporting uses tax-exclusive amounts. Missing tax mappings are input errors to report, not instructions for Populate to create master data.  
Defaults are net 30 days for customers and net 45 days for suppliers. For documents issued before 2026, settle fully within 90 days. For 2026 documents, sample intended settlement: 85% on/before due date, 10% 1–30 days late, and 5% unpaid at cutoff. If a sampled payment date is after cutoff, leave it unpaid at cutoff. Consequently the actual paid percentage at cutoff is derived and need not equal 95%. Use full payments only in v1.  
Create and post payments, connect them to the proper invoices/bills, and reconcile receivable/payable and bank/outstanding lines as required. A standalone payment or bank statement line does not prove that an invoice is paid. Supplier cash movements must have the correct outbound sign and accounts.  
Keep two analytic plans and the existing account external IDs:  
| | | |  
|-|-|-|  
| **Product category** | **Product Lines plan** | **Production type plan** |   
| Wands and wand components | Magical Gear | Manufactured |   
| Brooms | Magical Gear | Purchased |   
| Brewed potions and raw ingredients | Apothecary | Manufactured |   
| Consumables | Magical Gear | Purchased |   
   
Use the existing Purchased and Manufactured analytic accounts. The historical analytic_consu external ID identifies Purchased in this scenario. Each line receives 100% on one account in each plan. The two plan totals describe the same amount from different perspectives and must not be summed together.  
Apply and verify analytic distributions on customer and vendor invoice product lines. For cost-of-sales/profit reporting, confirm whether the pinned accounting flow carries the desired analytics to actual COGS entries. If it does not, the blueprint helper must supply a supported allocation. Do not treat purchases of components as final-product COGS or count both component consumption and finished-good COGS as the same expense.  
Analytics JSON uses database account IDs. Resolve account external IDs at runtime rather than copying the source workbook's numeric keys. Database-generated plan fields on budget lines must likewise be discovered and verified.  
**Budgets as an existing comparison dataset**  
Read the imported annual analytic budgets for comparisons. Populate does not create or rebase budgets, alter their amounts, or change the analytic plans. The existing budgets are independent of the generated actuals. Revenue and cost analytics must use the same accounts, signs, and plan meanings so the user can compare actuals with those budgets.  
For a partial-period comparison, phase the existing annual budget using the seasonal calendar and the 20 September cutoff. Do not rewrite annual budgets from realised invoices. Compare each analytic plan separately to avoid double-counting the same company amount.  
**12. Master data input contract**  
The user supplies and imports master data outside this specification. The blueprint consumes existing companies, partners, products, warehouses, locations, routes, operation types, BoMs, supplier relationships, CRM reference records, analytic accounts, and budgets.  
At startup, resolve the required records using their actual external IDs, validate counts and relationships, and report missing or ambiguous inputs. Use the installed model metadata for transaction fields. Do not create substitute records, silently change master configuration, or select an arbitrary record when a reference cannot be resolved.  
The blueprint needs working Inventory, Sales, Purchase, Manufacturing, Accounting, CRM, and Populate workflows. App installation, master-data import order, spreadsheet structure, import scripts, and preparation of master records are outside the transactional specification.  
**13. Populate implementation approach**  
Use the current XML Blueprint framework with create, write, and function operations, and a small custom helper/generator package for correlated event schedules, quotas, dependency allocation, and historical workflow handling. The older _populate_factories idea in the supplied Word document is not the implementation contract for this attempt. Populate supports custom generators, fixed seeds, scaling, and resumable sessions. [S1]  
Use seed **20260920**. Save the pinned revisions, blueprint version, configuration, timezone, cutoff, and seed with the run. Determinism also requires the same master-data candidates and worker strategy. Use stable sorting and explicit tie-breaking rather than database search order.  
Define the blueprint's base counts as a 1% pilot: 1,000 sale-order records, including 830 completed, 20 awaiting fulfilment, 100 cancelled, and 50 open. Use largest-remainder allocation for annual/geographic quotas. Provide a small curated edge-case fixture for all warehouses, supply types, statuses, and boundary dates if the 1% sample misses any. The agreed 100,000-order dataset is a 100× run from a clean master-data clone. Master data remains fixed and must not scale.  
Execution sequence:  
1. Validate master data, references, configuration, and the account/valuation prerequisites.  
2. Build deterministic demand, attribution, eligibility, and event schedules; persist a run-specific manifest and supply allocations.  
3. Create CRM and quotations with matching parties, teams, dates, and line prices.  
4. Confirm eligible sales through workflow. Trigger and process required purchases, production, and internal transfers, respecting event order.  
5. Complete eligible deliveries, create/post customer invoices and vendor bills, and process due payments and reconciliation.  
6. Apply only the historical date corrections established by the pilot. Recompute affected valuation/accounting where required.  
7. Validate counts, links, quantities, historical ordering, valuation, accounting, analytics, and visible trends.  
8. Snapshot the validated dataset and record report benchmark measurements.  
Do not create records directly in final business states as a substitute for running workflow. The attached test.xml needs revision: its CRM/SO parties and dates are independent, its confirmation filters exclude drafts, and it does not complete deliveries, invoices, bills, or payments. Its hard-coded currency ID and broad user/product domains also need removal.  
Start sequentially for stock and accounting work where chronology matters. Parallelise only proven-independent jobs. Disable notification/tracking side effects where appropriate, while preserving the business operations required to create the chain. Review the exact installed Populate syntax and method signatures before generating XML.  
Use Populate resume for interrupted sessions. A new full run on an already-populated database must not silently append a second copy. Restore a clean master-data snapshot for comparisons; do not perform broad destructive cleanup by business state alone.  
**14. Validation and performance acceptance**  
**Business and data integrity**  
- Exact sales totals: 100,000 overall; 83,000 completed/invoiced; 2,000 confirmed outstanding; 10,000 cancelled; 5,000 quotations. No empty orders.  
- Exactly 70,000 CRM-linked orders with matching customer, company, team, representative, and attribution. CRM outcome counts reconcile to section 8.  
- Every completed sales line has sufficient linked delivered quantity and a linked posted invoice line. Outstanding/cancelled/quotation populations have no completed customer delivery or customer invoice under the v1 rules.  
- Every received purchase has a coherent confirmed PO and vendor. Every posted vendor bill refers to received quantities; received-but-not-yet-billed recent goods may remain at cutoff.  
- Manufacturing output and actual component consumption match the applicable BoM. No component is consumed before availability; no negative historical stock is introduced to bypass supply.  
- No Phase 2 transaction before eligibility and no warehouse operation before opening. All realised events are within the scenario window and causal order. Future planned events remain uncompleted.  
- Each regional dispatch/receipt pair uses the intended transit location and conserves quantities. Internal transfer departure does not remove company ownership or create revenue.  
- Transit quantity is positive for the designated outstanding cohort at cutoff, and zero after receipt when inspecting a completed shipment's timeline. Historical quantity calculations agree with native stock reports for representative dates.  
- FIFO totals reconcile to the installed native valuation at the same reporting instant. Allocated warehouse/transit values sum to company/product value without double counting. Do not use current product cost as historical valuation.  
- Posted journal entries balance; receivable/payable residuals match actual reconciliation. Payment status cannot be established only by the existence of a payment record.  
- Each analytic plan allocates 100% of intended revenue/cost lines. Budgets and actuals use the same plan and sign conventions; costs are not duplicated across purchases, manufacturing, and COGS.  
- No unintended transactions are generated for excluded destination regions. Annual regional proportions and Europe's UK share meet rounding tolerances.  
**Visible trend checks**  
- Annual completed-order cohorts show the 2020 dip and 2021 expansion. Report any cross-year delivery/invoice timing differences rather than forcing every metric to share the same totals.  
- August and 1–20 September demand density exceed ordinary daily density, with the pattern visible in multiple years and 2026.  
- November 2020 Chocogrenouilles unit volume and revenue show the specified exception and reconcile to the campaign's transactions.  
- Regional order shares progress toward 50% Europe / 30% Americas / 20% Asia-Pacific. UK remains 60% of European confirmed orders.  
- Margin comparisons show both product-family differences and the 2022 cost-pressure effect; measure realised margins before presenting a predetermined claim.  
- 2026 comparisons consistently use the same cutoff period, and open pipeline is recent rather than ten-year-old unfinished work.  
**Reporting performance**  
Benchmark the same reports at pilot and full scale: monthly invoiced revenue by region/product, CRM conversion by source/team, fulfilment lead times, transit quantity/value at a historical date, and analytic actual-versus-budget.  
Record database size, per-model row counts, hardware, PostgreSQL version, Odoo revisions, query text/domain, elapsed time, returned row count, and cache conditions. Use repeated warm measurements and a documented cold-cache method when available; do not describe an unverified run as cold. Use EXPLAIN (ANALYZE, BUFFERS) for relevant read-only SQL in the disposable demo environment.  
Demonstrate the incorrect multiplication caused by joining sales lines, stock moves, and invoice lines at incompatible grains, then compare a correct solution aggregating each fact to the required grain before joining. Measure both correctness and speed. Avoid promising a specific slowdown merely because the dataset contains 100,000 orders.  
Large-volume performance requires realistic fact-table sizes, not inflated master data. Retain the small catalogue and partner population. If the full run is too fast to expose the intended reporting difference, increase transactional scale on a fresh clone after measuring the first dataset.  
**15. Blueprint implementation milestones**  
1. Resolve the imported scenario references and inspect transaction fields/methods on the installed revision.  
2. Implement deterministic demand quotas, correlated event schedules, and supply-allocation links.  
3. Prove historical dating, FIFO valuation, operational posting, and payment reconciliation on a small fixture.  
4. Run the 1% pilot and the correctness/performance checks in section 14.  
5. Generate the full 100,000-order dataset after the pilot passes, retaining the run manifest and reproducibility parameters.  
The minimum end-to-end fixture is one purchased resale product and one manufactured product sold from each warehouse, with an early-year direct international sale, a completed transit, an unfinished transit at cutoff, a cancelled quotation, a cancelled confirmed order, an open quotation, a posted/paid invoice, and an unpaid recent invoice. Include December/January and September-cutoff boundary cases.  
The existing Server Action is a possible later post-processing mechanism. Do not execute its legacy code unmodified. Any retained correction must operate only on generated records, preserve the historical event contract, and rerun valuation/accounting checks.  
**Sources**  
The user's later decisions take precedence over ideas in the original documents.  
- Supplied workbook: [RNG][OXP2026] Talk data _ Heavyweight DB.xlsx, considering only source sheets with an id column.  
- Supplied preliminary XML: test.xml,  
- **S1:**[Odoo master Populate documentation.](https://www.odoo.com/documentation/master/developer/reference/backend/populate.html "https://www.odoo.com/documentation/master/developer/reference/backend/populate.html")  
- **S2:**[Odoo master stock accounting product and FIFO implementation.](https://github.com/odoo/odoo/blob/master/addons/stock_account/models/product.py "https://github.com/odoo/odoo/blob/master/addons/stock_account/models/product.py")  
- [Odoo master warehouse implementation.](https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_warehouse.py "https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_warehouse.py")  
- [Odoo master locations and ](https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_location.py "https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_location.py")[procurement rules.](https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_rule.py "https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_rule.py")  
Public master is moving source, not the pinned revision of the user's database. Sources were inspected during preparation on 16–17 September 2026.  
