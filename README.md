
# 📄 Holistic Assessment Web App — Requirements and Analysis Document (Updated)

---

## 🔧 1. Project Overview

This project transforms the existing Excel-based Holistic Assessment Tool used by the Ghana Health Service (GHS) into a modular, configurable, DHIS2-integrated web application. It authenticates users using DHIS2 Basic Auth and retrieves relevant indicators or data elements based on administrator-defined configurations to calculate performance scores and render dashboards.

---

## 🎯 2. Objectives

* Authenticate users via **DHIS2 Basic Auth** (no internal user login system).
* Eliminate manual data entry by fetching indicator values directly from DHIS2.
* Compute trends, scores, target gaps, and performance categories.
* Visualize objective and sector performance via interactive dashboards.
* Support multi-level access (national, regional, district, sub-district, facility) via DHIS2 org unit assignments.
* Provide configurable control over indicators, formulas, targets, and weights.
* Export reports in Excel, CSV, and PDF with formatting and color codes.

---

## 👥 3. Stakeholders and User Roles

| Role                                | Permissions                                                              |
| ----------------------------------- | ------------------------------------------------------------------------ |
| **Super Admin**               | Configure instance URLs, DHIS2 connections, global settings              |
| **National Admin**            | Configure indicators, weights, targets, and manage users                 |
| **Regional User**             | View reports and dashboards for all districts/facilities in their region |
| **District User**             | View and assess sub-districts and facilities in their district           |
| **Facility User**             | View only their own facility                                             |
| **Anonymous/Guest**(optional) | View public dashboards if enabled                                        |

User identity, permissions, and org units are derived directly from the authenticated DHIS2 session via `/api/me`.

---

## 🧰 4. Functional Requirements

### 4.1 Authentication and Session Handling

* [X] Users log in using their DHIS2  **username, password** , and **instance URL** (e.g. `https://dhims.chimgh.org/dhims`)
* [X] No internal Django accounts or passwords are required
* [X] Backend sends Basic Auth header to `/api/me` on DHIS2 to verify credentials
* [X] On success, session is established and user org units/roles are stored

---

### 4.2 Configurable Indicator Registry

* [X] Admin can define **which indicators/data elements** to fetch via UI or Django Admin
* [X] Each indicator record includes:
  * DHIS2 UID
  * Name/label
  * Data type: `indicator`, `dataElement`, `calculated`
  * Optional formula (e.g. `(uid1 / uid2) * 100`)
  * Target value and target type (`increase` or `decrease`)
  * Color-coded scoring rules
  * Active/inactive toggle
* [X] Indicators marked as “active” are used in all computations and syncs

---

### 4.3 Org Unit Tree and Period Selection

* [X] Org unit tree fetched via `/api/organisationUnits`
* [X] Access limited to user’s root org unit and children
* [X] Period selector supports:
  * Monthly, quarterly, yearly
  * Relative periods (e.g. last 12 months, last 4 quarters)

---

### 4.4 Data Sync and Fetching

* [X] Data pulled from DHIS2 `/api/analytics.json` or other endpoints depending on indicator type
* [X] Queries are constructed using only UIDs of configured indicators
* [X] Background tasks (via Celery) handle bulk fetching, retries, and pre-processing

---

### 4.5 Trend, Scoring, and Target Gap Computation

* [X] System computes:
  * Year-over-year change
  * Gap to target
  * Trend direction
* [X] Assigns a score from –2 to +2 with rules defined in admin panel
* [X] Color-coded based on performance (customizable ranges):
  * Red: Severely Underperforming
  * Orange: Underperforming
  * Yellow: Sustained
  * Light Green: Moderately Performing
  * Green: Highly Performing

---

### 4.6 Objective and Sector Aggregation

* [X] Indicators grouped under objectives (e.g., Objective 1, 2, 3)
* [X] Objective scores are computed as **median of weighted indicator scores**
* [X] Overall sector score is weighted average of objective scores
* [X] Configurable weights via UI or Django Admin

---

### 4.7 Visualization & Dashboards

* [X] Dynamic dashboards for:
  * Objectives
  * Org units
  * Time periods
* [X] Include:
  * Gauges and bar charts
  * Scorecards
  * Color-coded trend indicators
  * Interactive drilldowns by org unit and indicator

---

### 4.8 Export and Reporting

* [X] Exports available in:
  * Excel (with conditional formatting)
  * CSV
  * PDF (with charts)
* [X] Exported reports reflect current filters (org unit, period)
* [X] Export logs stored per user

---

### 4.9 Admin Configuration Panel

* [X] Manage:
  * Tracked indicators
  * Weightings
  * Score logic
  * DHIS2 instance base URL (for system-wide default)
* [X] Optional: allow multi-tenant DHIS2 instance support per user

---

### 4.10 Audit Logs and History

* [X] Track:
  * All config changes (e.g., indicators added/edited)
  * Logins
  * Score overrides
  * Data fetch errors

---

## 🧱 5. Technical Architecture

| Layer                   | Stack                                       |
| ----------------------- | ------------------------------------------- |
| **Frontend**      | Next.js + TypeScript + Tailwind + shadcn/ui |
| **Backend**       | Django + Django REST Framework              |
| **Database**      | PostgreSQL                                  |
| **Job Queue**     | Celery + Redis                              |
| **DHIS2 API**     | Basic Auth (with `Authorization: Basic`)  |
| **Exports**       | openpyxl, pandas, pdfkit/reportlab          |
| **Session Store** | Django sessions / Redis                     |
| **Deployment**    | Docker + Gunicorn + NGINX                   |

---

## 🔐 6. Security Design

* Use HTTPS for all requests
* Discard DHIS2 password after authentication
* Do not cache `Authorization` headers long-term
* Use short-lived server-side sessions
* Rate-limit failed login attempts
* Protect admin/config endpoints with role-based control

---

## 🔁 7. Key Workflows

### Login Flow

1. User enters DHIS2 instance URL, username, and password
2. Django sends Basic Auth request to `/api/me`
3. If valid:
   * Fetch org units and authorities
   * Store session
   * Redirect user to dashboard scoped to their domain

### Data Sync

1. Background job or user action triggers sync
2. Pull active indicators’ UIDs from DB
3. Send analytics query to DHIS2
4. Apply any custom formulas or calculations
5. Compute scores and color codes
6. Store results in local DB or cache

### Admin Flow

1. Add/edit indicators via UI or Django Admin
2. Define:
   * UID
   * Label
   * Type
   * Formula
   * Targets
   * Weights
   * Scoring rules

### Reporting Flow

1. User selects org unit and period
2. Views dashboard and trend tables
3. Clicks export → downloads formatted Excel/CSV/PDF

---

## 📌 8. Configurable Elements (No Code Changes Required)

| Configurable Item       | Where Managed                            |
| ----------------------- | ---------------------------------------- |
| Indicator UIDs          | Admin panel / Django Admin               |
| Indicator formulas      | Admin panel                              |
| Target values and types | Admin panel                              |
| Scoring thresholds      | Admin panel                              |
| DHIS2 instance URLs     | User login form (or system-wide setting) |
| Org unit filters        | Derived from DHIS2 user metadata         |
| Visualization settings  | JSON or database-driven configuration    |
| Export formatting rules | Config in DB or YAML file                |

---

## ✅ 9. Future-Proofing and Enhancements

* Switch to OAuth2 authentication (when ready)
* Support multi-tenant DHIS2 instances with per-org configuration
* Add support for offline mode or PWA
* Enable AI-based anomaly detection on performance trends
* Real-time notifications for underperformance
