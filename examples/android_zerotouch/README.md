# Android Zero-touch Enrollment (Pattern)

This example models the automation pattern you described:
- ingest new device records (serial/IMEI/asset tag)
- assign devices to a configuration template
- produce an audit log + inventory export

In production, this would integrate with:
- Android Zero-touch portal / Android Management APIs
- Asset inventory system / CMDB

Files:
- `zerotouch_assign.py` – takes a CSV input and produces an assignment plan + audit log
