"""Single source of truth for every tunable number, weight, date range, and
master-data reference the planner uses.

Every other ``planner/*`` module imports its constants from here instead of
defining them locally - the *algorithms* (quota reconciliation, scheduling,
basket assembly, ...) live in their own domain files, but the *data* that
drives them lives in exactly one place. To change a distribution, a rate, a
lead time, or which xmlid a family/team/source maps to, edit this file only;
nothing else should need touching (the one exception is genuinely new
master-data records - e.g. a 17th product - which also need a snapshot
re-export, see ``README.md``).

Sections below are ordered to match the spec's own section numbers.
"""
from __future__ import annotations

from datetime import date, datetime

# ============================================================================
# Scenario scope (spec section 1)
# ============================================================================

SCENARIO_START = datetime(2016, 1, 1)
CUTOFF = datetime(2026, 9, 21, 0, 0, 0)  # exclusive, Europe/Brussels
TIMEZONE = 'Europe/Brussels'
SEED = 20260920

# Spec section 3: "Keep open quotations within the last 60 days of the
# scenario and outstanding confirmed orders within the last 45 days."
OPEN_QUOTATION_WINDOW_DAYS = 60
OUTSTANDING_WINDOW_DAYS = 45

# Pinned Odoo build this dataset was generated/validated against - written
# into the run manifest (spec section 13: "save the pinned revisions,
# blueprint version, configuration, timezone, cutoff, and seed with the
# run"). Update these after re-validating against a different snapshot.
ODOO_CORE_COMMIT = 'f63f1cca433b182d003f0ac4eb9f8e2efaad810d'
ODOO_ENTERPRISE_COMMIT = 'b8b09590ddb5a88f30fdd5249f4c830002abdc64'

# ============================================================================
# Section 3: volumes and outcomes
# ============================================================================

OUTCOMES = ('delivered', 'awaiting', 'cancelled', 'open')

ANNUAL = {
    2016: {'all': 1500, 'delivered': 1300, 'awaiting': 0, 'cancelled': 200, 'open': 0},
    2017: {'all': 1900, 'delivered': 1650, 'awaiting': 0, 'cancelled': 250, 'open': 0},
    2018: {'all': 2400, 'delivered': 2100, 'awaiting': 0, 'cancelled': 300, 'open': 0},
    2019: {'all': 3000, 'delivered': 2650, 'awaiting': 0, 'cancelled': 350, 'open': 0},
    2020: {'all': 2700, 'delivered': 2300, 'awaiting': 0, 'cancelled': 400, 'open': 0},
    2021: {'all': 8000, 'delivered': 7100, 'awaiting': 0, 'cancelled': 900, 'open': 0},
    2022: {'all': 11000, 'delivered': 9850, 'awaiting': 0, 'cancelled': 1150, 'open': 0},
    2023: {'all': 12500, 'delivered': 11000, 'awaiting': 0, 'cancelled': 1500, 'open': 0},
    2024: {'all': 14500, 'delivered': 13100, 'awaiting': 0, 'cancelled': 1400, 'open': 0},
    2025: {'all': 18000, 'delivered': 16450, 'awaiting': 0, 'cancelled': 1550, 'open': 0},
    2026: {'all': 24500, 'delivered': 15500, 'awaiting': 2000, 'cancelled': 2000, 'open': 5000},
}
ANNUAL_TOTAL = {
    outcome: sum(y[outcome] for y in ANNUAL.values())
    for outcome in ('all', 'delivered', 'awaiting', 'cancelled', 'open')
}
assert ANNUAL_TOTAL == {'all': 100_000, 'delivered': 83_000, 'awaiting': 2_000, 'cancelled': 10_000, 'open': 5_000}

# Spec section 3: cancellations split before/after confirmation (global, not per-year).
CANCEL_BEFORE_CONFIRM_SHARE = 0.80  # 8,000 / 10,000
CANCEL_AFTER_CONFIRM_SHARE = 0.20  # 2,000 / 10,000

# Spec section 3: outstanding confirmed orders' supply posture.
OUTSTANDING_SUB_BUCKETS = ('transit', 'production', 'purchase')
OUTSTANDING_FULL_SCALE_TOTALS = {'transit': 1000, 'production': 600, 'purchase': 400}

# Spec section 7: sales-line count distribution.
LINE_COUNT_WEIGHTS = {1: 0.10, 2: 0.20, 3: 0.30, 4: 0.20, 5: 0.15, 6: 0.05}

# ============================================================================
# Section 4: customer and supplier cohorts
# ============================================================================

# Proposed customer onboarding cohorts (Phase 2 only; Phase 1 is eligible
# from scenario start). Assignment to a specific cohort is not fixed by the
# spec - customers are sliced into cohorts in stable xmlid order.
PHASE2_COHORT_SIZES = {2021: 40, 2022: 24, 2023: 20, 2024: 16, 2025: 12, 2026: 8}
PHASE1_ELIGIBLE_FROM = date(2016, 1, 1)
PHASE2_SUPPLIER_ELIGIBLE_FROM = date(2021, 1, 1)

EUROPE_CODES = {
    'FR', 'DE', 'IT', 'ES', 'BG', 'SE', 'NO', 'DK', 'FI', 'PT', 'GR', 'AL', 'AT', 'IE', 'BE', 'NL',
    'LU', 'PL', 'CZ', 'SK', 'HU', 'RO', 'HR', 'SI', 'EE', 'LV', 'LT', 'MT', 'CY', 'IS', 'CH',
}
AMERICAS_CODES = {'US', 'CA', 'BR', 'MX', 'AR', 'PE', 'CL', 'CO', 'VE', 'UY', 'PY', 'BO', 'EC'}
APAC_CODES = {'SG', 'AU', 'CN', 'IN', 'JP', 'KR', 'TH', 'ID', 'NZ', 'MY', 'PH', 'VN', 'TW', 'HK'}
UK_CODE = 'GB'

# Spec section 7: 70% primary / 30% eligible-alternative supplier choice.
PRIMARY_SUPPLIER_SHARE = 0.70

# ============================================================================
# Section 5: geographic distribution
# ============================================================================

REGIONS = ('uk', 'other_europe', 'americas', 'apac')

# 2016-2020 share the same weights ("2016-2020" row in the spec table).
REGION_WEIGHTS = {
    **{y: {'europe': 0.80, 'americas': 0.15, 'apac': 0.05} for y in range(2016, 2021)},
    2021: {'europe': 0.70, 'americas': 0.20, 'apac': 0.10},
    2022: {'europe': 0.66, 'americas': 0.22, 'apac': 0.12},
    2023: {'europe': 0.62, 'americas': 0.24, 'apac': 0.14},
    2024: {'europe': 0.58, 'americas': 0.26, 'apac': 0.16},
    2025: {'europe': 0.54, 'americas': 0.28, 'apac': 0.18},
    2026: {'europe': 0.50, 'americas': 0.30, 'apac': 0.20},
}
UK_SHARE_OF_EUROPE = 0.60

# ============================================================================
# Section 7: products, prices, and seasonality
# ============================================================================

FAMILIES = ('wands', 'brooms', 'potions', 'consumables')
FAMILY_PRODUCTS = {
    'wands': ('prod_wand_holly', 'prod_wand_elder'),
    'brooms': ('prod_nimbus', 'prod_firebolt'),
    'potions': ('prod_felix', 'prod_polyjuice'),
    'consumables': ('prod_chocolate_frog', 'prod_gillyweed'),
}
BASE_FAMILY_WEIGHTS = {'wands': 0.20, 'brooms': 0.25, 'potions': 0.30, 'consumables': 0.25}
CALENDAR_GROUP = {'wands': 'wands_brooms', 'brooms': 'wands_brooms', 'potions': 'potions', 'consumables': 'consumables'}
DEFAULT_HOUR = 10

# (month, day_start, day_end_inclusive) -> {curve_group: multiplier}, "most of
# the year" defaults to 1.0 for every group.
SEASONAL_WINDOWS = [
    ((8, 1), (8, 31), {'wands_brooms': 2.5, 'consumables': 3.0, 'potions': 1.5}),
    ((9, 1), (9, 20), {'wands_brooms': 3.0, 'consumables': 4.0, 'potions': 1.5}),
    ((9, 21), (9, 30), {'wands_brooms': 1.5, 'consumables': 1.5, 'potions': 1.0}),
]

INDIVIDUAL_QTY_RANGE = {'wands': (1, 2), 'brooms': (1, 1), 'potions': (1, 3), 'consumables': (2, 8)}
CORPORATE_QTY_RANGE = {'wands': (3, 8), 'brooms': (1, 3), 'potions': (5, 15), 'consumables': (20, 60)}
INDIVIDUAL_DISCOUNT = 0.0
CORPORATE_DISCOUNT = 0.05
CORPORATE_SHARE = 0.20  # spec section 7, "where both customer types exist"

CHOCOGRENOUILLES_PRODUCT = 'prod_chocolate_frog'
CHOCOGRENOUILLES_WINDOW = (date(2020, 11, 1), date(2020, 11, 14))
CHOCOGRENOUILLES_MULTIPLIER = 4
CHOCOGRENOUILLES_CAMPAIGN = 'bi_campaign_frogs'

# Spec section 7: "Proposed 2026 net selling prices in EUR" - sellable
# finished goods only (not raw materials/components, which are never on a
# sale order line). These are the *2026 baseline*; SELLING_PRICE_FACTORS
# below scales them down for earlier years. Master data's own
# product.list_price should already carry these same values - kept here too
# as the single reference `pricing.py` uses, so the planner stays pure
# Python (no live Odoo read needed to plan prices).
PRODUCT_2026_LIST_PRICE = {
    'prod_wand_holly': 135.00,
    'prod_wand_elder': 360.00,
    'prod_nimbus': 280.00,
    'prod_firebolt': 675.00,
    'prod_felix': 210.00,
    'prod_polyjuice': 165.00,
    'prod_chocolate_frog': 7.50,
    'prod_gillyweed': 26.00,
}

# Spec section 7: "use year-specific price factors instead of applying
# current prices to old transactions". Selling factor applies at quotation
# date; vendor-cost factor applies at purchase confirmation.
SELLING_PRICE_FACTORS = {
    2016: 0.78, 2017: 0.80, 2018: 0.82, 2019: 0.85, 2020: 0.85,
    2021: 0.88, 2022: 0.92, 2023: 0.95, 2024: 0.97, 2025: 0.99, 2026: 1.00,
}
VENDOR_COST_FACTORS = {
    2016: 0.72, 2017: 0.74, 2018: 0.76, 2019: 0.79, 2020: 0.80,
    2021: 0.84, 2022: 0.94, 2023: 0.97, 2024: 0.98, 2025: 0.99, 2026: 1.00,
}
CURRENCY_DECIMALS = 2

# ============================================================================
# Section 8: CRM and commercial consistency
# ============================================================================

CRM_LINK_RATE = 0.70

# Extra, order-unlinked CRM volumes at full (100,000-order) scale (spec
# section 8's "Proposed CRM total is 120,000 records" - the 70,000 linked
# opportunities come from CRM_LINK_RATE above; these three are on top).
CRM_EXTRA_FULL_SCALE = {
    'lost_no_quote': 40_000,
    'open_no_quote': 6_000,
    'unconverted_leads': 4_000,
}

# Matches the workbook's utm.medium per utm.source (spec: "Match medium to source").
SOURCE_MEDIUM = {
    'bi_source_prophet': 'bi_medium_print',
    'bi_source_owl': 'bi_medium_email',
    'bi_source_referral': 'bi_medium_referral',
    'bi_source_web': 'bi_medium_web',
}
SOURCE_WEIGHTS_BEFORE_2021 = {'bi_source_prophet': 0.45, 'bi_source_owl': 0.25, 'bi_source_referral': 0.20, 'bi_source_web': 0.10}
SOURCE_WEIGHTS_FROM_2021 = {'bi_source_prophet': 0.20, 'bi_source_owl': 0.25, 'bi_source_referral': 0.20, 'bi_source_web': 0.35}

TEAMS = {
    'team_gryffindor': ('user_g_1', 'user_g_2', 'user_g_3'),
    'team_hufflepuff': ('user_h_1', 'user_h_2', 'user_h_3'),
    'team_ravenclaw': ('user_r_1', 'user_r_2', 'user_r_3'),
    'team_slytherin': ('user_s_1', 'user_s_2', 'user_s_3'),
}

LOST_REASON_WEIGHTS = {
    'bi_loss_price': 0.40,
    'bi_loss_timing': 0.25,
    'bi_loss_competitor': 0.25,
    'bi_loss_no_need': 0.10,
}

CRM_STAGE_NEW = 'bi_crm_new'

# ============================================================================
# Section 6/9/10: warehouses, lead times, and the historical date contract
# ============================================================================

PRODUCTION_LEAD_DAYS = (1, 4)
PURCHASE_LEAD_DAYS = (5, 12)
PURCHASE_CONFIRM_DELAY_DAYS = (0, 2)
EU_DELIVERY_DAYS = (1, 3)
REGIONAL_DELIVERY_DAYS = (2, 5)  # from a regional warehouse, once received
DIRECT_TRANSIT_DAYS = {  # pre-2021 direct Belgium -> region, no regional warehouse leg
    'americas': (8, 16),
    'apac': (12, 22),
}
REGIONAL_TRANSIT_DAYS = {  # Belgium -> transit location, once the warehouse exists
    'uk': (2, 5),
    'americas': (8, 16),
    'apac': (12, 22),
}
LATE_DELIVERY_SHARE = 0.10
LATE_DELIVERY_EXTRA_DAYS = (2, 5)
INVOICE_AFTER_DELIVERY_DAYS = (0, 2)

# Warehouse opening dates (spec section 6) - code -> operational-from date.
WAREHOUSE_OPENING = {
    'BE': date(2016, 1, 1),
    'UK': date(2016, 1, 1),
    'US': date(2021, 1, 1),
    'SG': date(2021, 1, 1),
}

# Destination region -> its dedicated regional warehouse code, or None if the
# region has no regional warehouse and is always served directly from BE
# ("other Europe is always served directly from Belgium", spec section 6).
REGION_WAREHOUSE = {'uk': 'UK', 'other_europe': None, 'americas': 'US', 'apac': 'SG'}

# ============================================================================
# Section 11: accounting, payments, and analytics
# ============================================================================

CUSTOMER_NET_DAYS = 30
VENDOR_NET_DAYS = 45
FULL_SETTLEMENT_DAYS = 90  # pre-2026 documents settle within this window
ON_TIME_SHARE_2026 = 0.85
LATE_1_30_SHARE = 0.10
UNPAID_SHARE = 0.05
VENDOR_BILL_AFTER_RECEIPT_DAYS = (0, 5)
