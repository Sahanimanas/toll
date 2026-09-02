"""Toll-plaza domain layer.

This package extends the ANPR platform backend with MLFF tolling: FASTag
accounts, toll transactions, rates, lanes, violations, NPCI reconciliation,
reports, NMS and a compatibility REST API (mounted at ``/api``) that
reproduces the exact HTTP contract the toll-plaza React frontend expects.

The ANPR pipeline publishes recognitions to ``/api/v1/ingest/recognitions``
as before; a hook (``app.toll.service.on_recognition``) converts each
recognition into a toll transaction (rate lookup + FASTag deduction) and
pushes it to subscribed frontends over SSE (``/api/anpr/stream``).
"""
