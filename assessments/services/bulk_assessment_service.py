"""
Background job runner for bulk-generating Holistic Assessments across every
facility in a DHIS2 organisation unit group (e.g. "every District Hospital in
my region"), instead of a user repeating the single-facility flow manually.

Reuses RealTimeDHIS2Service.fetch_holistic_assessment_data as a pure black box
per facility - scoring logic is never touched here.
"""
import logging
import threading

from django.db import close_old_connections
from django.utils import timezone

from dhis2_auth.dhis_client import DHIS2ClientFactory
from .real_time_service import RealTimeDHIS2Service

logger = logging.getLogger(__name__)

# Facilities are processed one at a time, not concurrently. A single facility's
# fetch_holistic_assessment_data call already opens its own internal concurrency
# (up to 3 workers for batch chunks, up to 5 for the miss-prefetch pass - see
# real_time_service.py) - stacking facility-level concurrency on top of that
# would multiply total DHIS2 load directly, which is exactly what this feature
# exists to avoid given DHIS2's observed instability under load. A single named
# constant so it's trivial to raise later if that changes.
BULK_FACILITY_CONCURRENCY = 1

# With no facility-level parallelism, an unbounded target set could run for
# hours. Keep batches to a size that finishes in a reasonable session instead
# of silently accepting "every facility in the country".
MAX_BULK_FACILITIES = 150


def resolve_target_org_units(client, session_data, group_id, level=None):
    """
    Resolve the facilities a bulk job should target: members of the given
    DHIS2 org unit group, optionally narrowed by level, intersected with the
    requesting user's own DHIS2 org unit assignment(s) - the same access scope
    as the single-facility tree picker, so bulk generation can't reach outside
    what a user is otherwise allowed to see.

    Returns a list of {'id', 'name', 'level', 'path'} dicts sorted by name,
    deduped across the user's (usually one, occasionally more) assigned roots.
    """
    user_org_units = [ou for ou in session_data.get('org_units', []) if ou.get('id')]
    if not user_org_units:
        return []

    merged = {}
    for ou in user_org_units:
        root = client.get_org_unit_by_id(ou['id'])
        root_path = root.get('path') if root else None
        if not root_path:
            logger.warning(
                f"Could not resolve path for user org unit {ou['id']} - "
                "skipping it as a bulk-generation scope root"
            )
            continue

        for match in client.get_org_units_by_group(group_id, level=level, root_path=root_path):
            merged[match['id']] = match

    return sorted(merged.values(), key=lambda unit: unit.get('name', ''))


def start_bulk_assessment_job(job_id):
    """Spawn the background thread that processes a BulkAssessmentJob."""
    threading.Thread(target=run_bulk_assessment_job, args=(job_id,), daemon=True).start()


def run_bulk_assessment_job(job_id):
    """
    Process every PENDING item on a BulkAssessmentJob sequentially. For each
    facility: fetch its assessment data via the existing, untouched
    fetch_holistic_assessment_data pipeline, save it as a SavedAssessment
    (matching the exact flat indicator_data shape and period-name convention
    the interactive save flow already uses - see the module docstring in
    assessments/models.py's BulkAssessmentJob for why that shape matters), and
    record the outcome on the item. One facility failing (e.g. a DHIS2
    timeout) is recorded and the batch moves on - it never aborts the run.

    Runs on a plain background thread (no Celery/Redis) - Render's free tier
    has no worker service to run one on, matching export_excel_async's
    existing pattern exactly, including building its own DHIS2Client from the
    session key (the original request doesn't survive past the HTTP response)
    and a FakeSession/FakeRequest shim so the shared service layer doesn't
    need a real Django request object.
    """
    from ..models import BulkAssessmentJob, BulkAssessmentJobItem, SavedAssessment

    close_old_connections()
    try:
        job = BulkAssessmentJob.objects.select_related('created_by').get(id=job_id)
    except BulkAssessmentJob.DoesNotExist:
        logger.error(f"run_bulk_assessment_job: job {job_id} not found")
        return

    if not job.created_by:
        job.mark_failed("Job has no associated user - the account may have been removed.")
        return

    job.mark_started()

    try:
        client = DHIS2ClientFactory.create_client_from_session(
            job.created_by.dhis2_instance_url, job.session_key
        )
        service = RealTimeDHIS2Service(client)
        fake_session = type('FakeSession', (), {'session_key': job.session_key})()
        fake_request = type('FakeRequest', (), {'session': fake_session, 'data': {}})()

        pending_items = job.items.filter(status=BulkAssessmentJobItem.Status.PENDING).order_by('order', 'id')

        for item in pending_items:
            close_old_connections()

            job.refresh_from_db(fields=['cancel_requested'])
            if job.cancel_requested:
                job.items.filter(status=BulkAssessmentJobItem.Status.PENDING).update(
                    status=BulkAssessmentJobItem.Status.SKIPPED
                )
                break

            item.status = BulkAssessmentJobItem.Status.IN_PROGRESS
            item.started_at = timezone.now()
            item.attempt_count += 1
            item.save(update_fields=['status', 'started_at', 'attempt_count'])

            try:
                assessment_config = {
                    'org_unit_ids': [item.org_unit_id],
                    'org_unit_names': [item.org_unit_name],
                    'periods': job.periods,
                }
                payload = service.fetch_holistic_assessment_data(fake_request, assessment_config)
                data = payload[0]

                # Flatten into indicator-id-keyed dict with embedded objective
                # info - the exact shape the interactive save flow produces
                # (app/dashboard/assessment/page.tsx) and get_assessment_by_id
                # expects when re-hydrating a saved assessment for "View".
                flat_indicator_data = {}
                total_indicators = 0
                for objective in data.get('objectives', []):
                    for indicator in objective.get('indicators', []):
                        total_indicators += 1
                        flat_indicator_data[str(indicator['id'])] = {
                            **indicator,
                            'objective_id': objective['id'],
                            'objective_name': objective['name'],
                        }

                saved = SavedAssessment.objects.create(
                    name=f"{item.org_unit_name} - {', '.join(job.period_labels)}",
                    org_unit_id=item.org_unit_id,
                    org_unit_name=data.get('org_unit_name') or item.org_unit_name,
                    periods=job.period_labels,
                    indicator_data=flat_indicator_data,
                    calculated_scores={},
                    metadata={
                        'org_unit_ids': [item.org_unit_id],
                        'org_unit_names': [item.org_unit_name],
                        'source': 'bulk_generate',
                        'bulk_job_id': job.id,
                        'total_indicators': total_indicators,
                        'total_objectives': len(data.get('objectives', [])),
                    },
                    created_by=job.created_by,
                    session_key=job.session_key,
                )

                item.status = BulkAssessmentJobItem.Status.COMPLETED
                item.saved_assessment = saved
                item.completed_at = timezone.now()
                job.succeeded_facilities += 1
            except Exception as exc:
                logger.error(f"Bulk job {job.id} item {item.id} ({item.org_unit_name}) failed: {exc}")
                item.status = BulkAssessmentJobItem.Status.FAILED
                item.error_message = str(exc)[:2000]
                item.completed_at = timezone.now()
                job.failed_facilities += 1

            item.save(update_fields=['status', 'saved_assessment', 'error_message', 'completed_at'])
            job.processed_facilities += 1
            job.update_progress()

        job.mark_finished()

    except Exception as exc:
        logger.error(f"Bulk job {job_id} failed at the job level: {exc}")
        job.mark_failed(str(exc))
    finally:
        close_old_connections()
