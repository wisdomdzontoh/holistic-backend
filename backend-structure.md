# Holistic Assessment App - Django Backend Project Structure

backend/                # Root Django project
├── config/                      # Django settings and project config
│   ├── __init__.py
│   ├── settings.py              # Main project settings
│   ├── urls.py                  # Root URL config
│   └── wsgi.py
│
├── dhis2_auth/                 # App handling DHIS2 login and session
│   ├── models.py               # Optional: DHIS2User (if caching user info)
│   ├── views.py                # LoginView, LogoutView
│   ├── dhis_client.py          # Handles all HTTP calls to DHIS2
│   ├── session.py              # Session/token handling, headers
│   └── urls.py
│
├── indicators/                 # Core app managing indicators and scoring
│   ├── models.py               # TrackedIndicator, IndicatorFormula
│   ├── services.py             # Scoring logic, trend analysis
│   ├── serializers.py          # DRF serializers for APIs
│   ├── views.py                # APIs for indicators
│   └── admin.py                # Admin interfaces
│
├── assessments/               # Handles computed scores and visual summaries
│   ├── models.py               # IndicatorScore, ObjectiveScore, SectorScore
│   ├── services.py             # Score computation logic
│   ├── serializers.py
│   ├── views.py                # View/export scorecards, dashboards
│   └── admin.py
│
├── organisation/              # Handles org units and user scope
│   ├── models.py               # OrgUnit (optional local cache)
│   ├── services.py             # Tree parser, unit filtering
│   ├── serializers.py
│   └── views.py
│
├── exports/                   # Handles Excel, CSV, PDF generation
│   ├── services.py             # Report rendering logic
│   ├── templates/              # PDF templates, export layouts
│   └── views.py                # Download/export endpoints
│
├── configurations/                   # Admin-configurable weights, targets, rules
│   ├── models.py               # ScoringRules, WeightingScheme
│   ├── admin.py
│   ├── views.py
│   └── serializers.py
│
├── scheduler/                 # Background jobs and periodic tasks
│   ├── tasks.py                # Celery jobs: DHIS2 fetch, re-score
│   └── worker.py               # Celery app config
│
├── core/                      # Shared utilities and base classes
│   ├── exceptions.py
│   ├── mixins.py
│   ├── permissions.py
│   └── utils.py
│
├── manage.py
└── requirements.txt

# -----------------------------

# Models Summary (Core Fields)

# -----------------------------

# dhis2_auth.models (optional cache)

class DHIS2User(models.Model):
    username = models.CharField()
    org_units = models.JSONField()
    last_login = models.DateTimeField(auto_now=True)
    instance_url = models.URLField()

# indicators.models

class TrackedIndicator(models.Model):
    uid = models.CharField()                   # DHIS2 UID
    name = models.CharField()
    type = models.CharField(choices=[('indicator', 'Indicator'), ('dataElement', 'Data Element'), ('calculated', 'Calculated')])
    formula = models.TextField(blank=True)     # For derived indicators
    target_value = models.FloatField()
    target_type = models.CharField(choices=[('increase', 'Increase'), ('decrease', 'Decrease')])
    scoring_rule = models.ForeignKey('configs.ScoringRule', on_delete=models.SET_NULL, null=True)
    active = models.BooleanField(default=True)

# assessments.models

class IndicatorScore(models.Model):
    indicator = models.ForeignKey('indicators.TrackedIndicator', on_delete=models.CASCADE)
    org_unit = models.CharField()              # DHIS2 OrgUnit UID
    period = models.CharField()               # E.g., 2024Q3
    raw_value = models.FloatField()
    target_value = models.FloatField()
    score = models.IntegerField()             # -2 to +2
    change_pct = models.FloatField()
    gap_to_target = models.FloatField()
    color_code = models.CharField()

class ObjectiveScore(models.Model):
    objective = models.CharField()             # E.g. "Objective 1"
    org_unit = models.CharField()
    period = models.CharField()
    median_score = models.FloatField()
    weight = models.FloatField()

class SectorScore(models.Model):
    org_unit = models.CharField()
    period = models.CharField()
    score = models.FloatField()
    classification = models.CharField()

# configs.models

class ScoringRule(models.Model):
    name = models.CharField()
    lower_bound = models.FloatField()
    upper_bound = models.FloatField()
    score_value = models.IntegerField()
    color_code = models.CharField()

class WeightingScheme(models.Model):
    objective = models.CharField()
    weight = models.FloatField()
    indicator = models.ForeignKey('indicators.TrackedIndicator', on_delete=models.CASCADE)

# organisation.models (optional local cache)

class OrgUnit(models.Model):
    uid = models.CharField()
    name = models.CharField()
    parent_uid = models.CharField()
    level = models.IntegerField()
    path = models.TextField()
