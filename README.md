
# 📄 Holistic Assessment Web App — Requirements and Analysis Document (Updated)

---

## 🔧 1. Project Overview

This project transforms the existing Excel-based Holistic Assessment Tool used by the Ghana Health Service (GHS) into a modular, configurable, DHIS2-integrated web application. It authenticates users using DHIS2 Basic Auth and retrieves relevant indicators or data elements based on administrator-defined configurations to calculate performance scores and render dashboards.

**Key Innovation**: The application maintains the exact Excel-based interface while adding web-based advantages like DHIS2 integration, collaborative editing, and real-time scoring.

---

## 🎯 2. Objectives

* Authenticate users via **DHIS2 Basic Auth** (no internal user login system).
* **Replicate Excel Interface**: Maintain exact visual layout and functionality of the original Excel tool.
* Eliminate manual data entry by fetching indicator values directly from DHIS2 (80% of data).
* Allow manual data entry for non-DHIS2 indicators (20% of data).
* Compute trends, scores, target gaps, and performance categories automatically.
* Support multiple assessment periods (monthly, quarterly, half-yearly, yearly).
* Provide configurable control over indicators, formulas, targets, and weights.
* Enable save/load functionality for assessment progress.
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

### 4.2 Holistic Assessment Interface

* [ ] **Excel-like Table Interface**: Replicate exact layout from Excel tool
  * **Column Structure**: 
    * Column A (#): Row numbers and indicator IDs
    * Column B (Indicator): Descriptions, objectives, milestones
    * Columns C-G (Performance Trend): Period columns (e.g., 2020, 2021, 2023, 2024, 2025)
    * Column H (Change): Calculated percentage change
    * Column I (P-T Gap Analysis): Performance-to-Target gap
    * Column J (Target): Target values (various formats)
    * Column K (Outcome): Assessed score (-2, -1, 0, +1, +2) with color coding
    * Column U (Remarks): User comments/notes
  * **Hierarchical Structure**:
    * Milestones (MS): High-level goals (yellow background)
    * Objectives: Sub-goals under milestones (orange background)
    * Indicators: Specific metrics numbered under objectives
  * **Editable Cells**: Allow manual data entry for non-DHIS2 indicators
  * **Auto-calculated Cells**: Change, Gap Analysis, Assessed Score

* [ ] **Period Selection**:
  * Support multiple period types: Monthly, Quarterly, Half-yearly, Yearly
  * Minimum 3 periods required (e.g., 2021, 2022, 2023 OR Q1-2021, Q1-2022, Q1-2023)
  * Dynamic column generation based on selected periods

* [ ] **Assessment Workflow**:
  1. User navigates to Holistic Assessment page
  2. Selects assessment period type and periods (minimum 3)
  3. Clicks "Generate Report" to fetch DHIS2 data
  4. System populates table with DHIS2 data and empty cells for manual entry
  5. Users can edit non-DHIS2 indicator cells
  6. Real-time scoring calculation as data is entered
  7. Save progress functionality
  8. Export to Excel/PDF with current state

---

### 4.3 Configurable Indicator Registry

* [X] Admin can define **which indicators/data elements** to fetch via UI or Django Admin
* [X] Each indicator record includes:
  * DHIS2 UID
  * Name/label
  * Data type: `indicator`, `dataElement`, `calculated`
  * Optional formula (e.g. `(uid1 / uid2) * 100`)
  * Target value and target type (`increase` or `decrease`)
  * Color-coded scoring rules
  * Active/inactive toggle
* [X] Indicators marked as "active" are used in all computations and syncs

---

### 4.4 Data Sync and Fetching

* [X] Data pulled from DHIS2 `/api/analytics.json` or other endpoints depending on indicator type
* [X] Queries are constructed using only UIDs of configured indicators
* [X] Background tasks (via Celery) handle bulk fetching, retries, and pre-processing
* [ ] **Conflict Resolution**: Handle conflicts between manual entries and DHIS2 updates

---

### 4.5 Trend, Scoring, and Target Gap Computation

* [X] System computes:
  * Year-over-year change
  * Gap to target
  * Trend direction
* [X] Assigns a score from –2 to +2 with rules defined in admin panel
* [X] Color-coded based on performance (customizable ranges):
  * Red: Severely Underperforming (-2)
  * Orange: Underperforming (-1)
  * Yellow: Sustained (0)
  * Light Green: Moderately Performing (+1)
  * Green: Highly Performing (+2)

---

### 4.6 Objective and Sector Aggregation

* [X] Indicators grouped under objectives (e.g., Objective 1, 2, 3)
* [X] **Milestones**: Additional field for each objective, displayed at the end of objective indicators
* [X] Objective scores are computed as **median of weighted indicator scores**
* [X] Overall sector score is weighted average of objective scores
* [X] Configurable weights via UI or Django Admin

---

### 4.7 Save/Load Functionality

* [ ] **Assessment Sessions**: Save current assessment state
* [ ] **Progress Tracking**: Resume from where user left off
* [ ] **Version Control**: Track changes and allow rollback
* [ ] **Collaborative Editing**: Multiple users can work on same assessment

---

### 4.8 Export and Reporting

* [X] Exports available in:
  * Excel (with conditional formatting matching original)
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
* [ ] **Assessment History**: Track all saved assessments and changes

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

### Holistic Assessment Flow

1. User navigates to Holistic Assessment page
2. Selects assessment period type and periods (minimum 3)
3. Clicks "Generate Report"
4. System fetches DHIS2 data for configured indicators
5. Displays Excel-like table with:
   * Pre-populated DHIS2 data
   * Empty cells for manual entry
   * Auto-calculated scores and gaps
6. User can edit non-DHIS2 indicator cells
7. Real-time scoring updates
8. Save progress or export final report

### Data Sync

1. Background job or user action triggers sync
2. Pull active indicators' UIDs from DB
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
| Assessment periods      | User selection (monthly, quarterly, etc.) |

---

## ✅ 9. Future-Proofing and Enhancements

* Switch to OAuth2 authentication (when ready)
* Support multi-tenant DHIS2 instances with per-org configuration
* Add support for offline mode or PWA
* Enable AI-based anomaly detection on performance trends
* Real-time notifications for underperformance
* Advanced collaboration features (comments, approvals)
* Mobile-responsive assessment interface
* Integration with other health information systems

---

## 🎨 10. UI/UX Requirements

### Navigation Structure
- **Dashboard**: Overview, reports, analytics
- **Holistic Assessment**: Main Excel-like interface
- **Configuration**: Admin settings (role-based access)

### Holistic Assessment Interface
- **Exact Excel replication** with same visual layout
- **Editable cells** with validation and real-time feedback
- **Color coding** for scores and performance levels
- **Hierarchical grouping** (Milestones → Objectives → Indicators)
- **Period selection** with dynamic column generation
- **Save/Load functionality** with progress indicators
- **Export options** with formatting preservation

### Responsive Design
- **Desktop-first** for assessment interface (Excel-like experience)
- **Mobile-responsive** for dashboard and navigation
- **Touch-friendly** controls where appropriate

---

## 🔄 11. Development Phases

### Phase 1: Core Infrastructure ✅
- [X] Django backend setup
- [X] DHIS2 authentication
- [X] Basic dashboard pages
- [X] UI component library

### Phase 2: Holistic Assessment Interface 🔄
- [ ] Create Holistic Assessment page
- [ ] Build Excel-like table component
- [ ] Implement period selection
- [ ] Add editable cells functionality
- [ ] Real-time scoring calculation

### Phase 3: Backend Integration
- [ ] DHIS2 data fetching for configured indicators
- [ ] Scoring logic implementation
- [ ] Save/Load functionality
- [ ] Export system

### Phase 4: Advanced Features
- [ ] Collaborative editing
- [ ] Version control
- [ ] Advanced analytics
- [ ] Mobile optimization

---

This roadmap ensures you're building foundational services first (auth, config), then moving into domain-specific logic (indicators, scoring), and finally into visualizations, exports, and automation.
