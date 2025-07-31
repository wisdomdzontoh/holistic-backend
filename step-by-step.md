
This roadmap ensures you're building foundational services first (auth, config), then moving into domain-specific logic (indicators, scoring), and finally into visualizations, exports, and automation.

---

# ✅ Stepwise App Development Plan (Django)

---

## 🟩 Phase 1 – Core Project Setup

 **Goal** : Lay the foundation for the project and enable user authentication via DHIS2.

### ✅ 1. `config/` (project root)

* Set up Django project and settings
* Enable CORS, Redis, PostgreSQL, Celery
* Configure logging, DRF, static/media files

---

## 🟦 Phase 2 – DHIS2 Integration and Authentication

 **Goal** : Let users log in via DHIS2 Basic Auth; no internal Django users.

### ✅ 2. `dhis2_auth/`

**Build:**

* `LoginView`: accepts DHIS2 instance URL, username, password
* `dhis_client.py`: central client for calling `/api/me`, `/api/analytics`, etc.
* `session.py`: stores user/org metadata in Django session
* Optional `DHIS2User` model to track usage and metadata

 **Dependencies** :

* Enable middleware to check session validity
* Add session expiration and logout logic

---

## 🟨 Phase 3 – Indicator & Configuration Management

 **Goal** : Admins define which indicators/data elements to fetch from DHIS2 and how to interpret them.

### ✅ 3. `indicators/`

**Build:**

* `TrackedIndicator` model: uid, type, formula, target, target_type, active
* `IndicatorSerializer`, `IndicatorViewSet`: for API access
* Admin interface for adding/editing tracked indicators

**Optional:**

* UI form for entering complex indicator formulas (expression builder)

---

### ✅ 4. `configs/`

**Build:**

* `ScoringRule`: maps performance ranges (gap/change) → score and color
* `WeightingScheme`: links indicators to objectives with weights
* Admin form to manage:
  * Objective weights
  * Score thresholds
  * Classification labels (e.g. "Sustained", "Underperforming")

---

## 🟧 Phase 4 – Data Sync and Score Engine

 **Goal** : Pull data from DHIS2 and compute indicator scores, objective medians, and sector performance.

### ✅ 5. `assessments/`

**Build:**

* `IndicatorScore`: stores raw values, target gap, percent change, score, color
* `ObjectiveScore`, `SectorScore`: median/wtd. score per period
* `services.py`: scoring engine (based on configs)
* Admin override capability for manually adjusting indicator scores

 **Views** :

* Endpoint to trigger sync (protected)
* Endpoint to view computed scores (per indicator/org/period)

---

## 🟫 Phase 5 – Org Unit Access Control

 **Goal** : Allow scoped access based on DHIS2 org unit hierarchy.

### ✅ 6. `organisation/`

**Build:**

* Optional `OrgUnit` cache model (if you want local org tree)
* `get_user_org_tree()` function using `/api/organisationUnits`
* Utility for restricting access to indicator scores and dashboards

---

## 🟪 Phase 6 – Dashboards and Reporting APIs

 **Goal** : Provide frontend with scoped, color-coded dashboard data.

### ✅ 7. Extend `assessments/` views

* Dashboards per:
  * Org unit
  * Objective
  * Time period
* Include:
  * Score value
  * Color class
  * Classification label

**Build endpoints:**

* `/api/dashboard/objectives/`
* `/api/dashboard/indicators/`
* `/api/dashboard/sector/`

---

## 🟥 Phase 7 – Data Export

 **Goal** : Let users export results to Excel, CSV, and PDF with styles.

### ✅ 8. `exports/`

**Build:**

* Export functions using `openpyxl`, `pandas`, `pdfkit` or `WeasyPrint`
* Export layout templates (match Excel tool)
* Export endpoints (GET w/ filters):
  * `/export/excel/`
  * `/export/pdf/`
  * `/export/csv/`

---

## 🟦 Phase 8 – Automation (Optional / Parallel)

### ✅ 9. `scheduler/`

**Build:**

* `tasks.py`: Celery jobs for:
  * Pulling DHIS2 indicator values
  * Recomputing scores
* Management command or dashboard button to re-sync manually
* Cron/Django admin controls for schedule frequency

---

## 🚀 Final Wrap-Up: Testing, Admin Polishing, Docs

### ✅ 10. Testing, Logging, Versioning

* Add `pytest`, `factory_boy` for score engine testing
* Add audit logs for scoring overrides, config changes
* Create migration and data seeders for dev

---

### 📝 Summary Table

| Phase | App              | Purpose                             |
| ----- | ---------------- | ----------------------------------- |
| 1     | `config`       | Core Django setup                   |
| 2     | `dhis2_auth`   | User login via DHIS2 Basic Auth     |
| 3     | `indicators`   | Manage tracked indicators           |
| 4     | `configs`      | Scoring logic, weights              |
| 5     | `assessments`  | Data pull, score calculation        |
| 6     | `organisation` | Org unit scoping and access         |
| 7     | `assessments`  | Dashboard APIs                      |
| 8     | `exports`      | Report exports (Excel/PDF/CSV)      |
| 9     | `scheduler`    | Background data fetch, scoring jobs |
| 10    | All              | Tests, audits, seeding, deployment  |

---

Let me know if you'd like me to now scaffold out:

* Sample models per app
* API endpoint structure with DRF routers
* Unit test plan or API test cases
* Matching frontend route plan (for Next.js)
