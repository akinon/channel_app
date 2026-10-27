# Release Notes

## 0.0.161 (upgrading from 0.0.159)

Versions 0.0.160 - 0.0.161 are covered here.

### Breaking
- **Python 3.10 or newer is required** (`python_requires=">=3.10"`).
- **`OMNITRON_URL` must start with `https://`.** Importing
  `channel_app.core.settings` raises `ValueError` otherwise.

### Changed
- `requests` and `sentry-sdk` are no longer pinned to exact versions:
  `requests>=2.33.0`, `sentry-sdk>=2.8.0`.
- `OperationalEventDto.from_error_report` attaches `raw_data` only to failed
  reports (`is_ok=False`). API keys, tokens, passwords, e-mails and phone
  numbers in `raw_request` / `raw_response` are masked. New helper:
  `channel_app.core.data.mask_sensitive_data`.
- `ProcessOrderBatchRequests` commits the `version_date` fetched by
  `GetOrders` instead of the current one. Changes made to an order during the
  run are no longer marked as synced, so they are picked up on the next run.
- PyPI publishing runs only on `v*` tags and runs the tests first.

### Upgrade steps
1. Make sure your channel project runs on Python 3.10 or newer.
2. Set `channel_app==0.0.161` in your channel project `requirements.txt`.
3. If you set `OMNITRON_URL`, make sure it starts with `https://`.
4. If you pinned `requests` or `sentry-sdk` below the new minimums, raise them.

## 0.0.159 (upgrading from 0.0.155)

Versions 0.0.156 - 0.0.159 are covered here. No breaking changes.
All new behavior is opt-in or additive.

### New
- **Operational events.** Every `create_error_report` call in the services
  (order, product, product stock, product price, product image, setup) is now
  followed by `create_operational_event`. New `OperationalEventDto`
  (`OperationalEventDto.from_error_report(report)`), and new commands
  `CreateOperationalEvent` and `GetOperationalEvents`
  (`channel_app.omnitron.commands.operational_events`).
- **Out-of-stock filter.** `ProductService.insert_products(...,
  filter_out_of_stock_products=False)`. When `True`, products with zero or
  empty stock are marked as failed and reported instead of being sent.
- **Bulk attribute commands.** `BulkCreateOrUpdateAttributes`,
  `BulkCreateOrUpdateCategoryAttributes`, `GetLeafCategoryNodeIds`, and
  `SetupService.bulk_create_or_update_attributes()`.
- **`OMNITRON_URL` environment variable** overrides the default
  `https://{MAIN_APP_URL}/`.
- `pyproject.toml` and `uv.lock` for `uv` based installs.
- Docs: flows, terminology and operational event command reference.

### Changed
- `SetupService.create_or_update_category_attributes(max_workers=8)` now
  fetches category attributes in parallel and only for **leaf** categories.
  It calls `bulk_create_or_update_category_attributes` instead of
  `create_or_update_category_attributes`.
- CI image moved to Python 3.11.9. `tox.ini` adds py310 and py311.

### Upgrade steps
1. Set `channel_app==0.0.159` in your channel project `requirements.txt`.
2. If you override `SetupService` or call the category attribute action key
   `create_or_update_category_attributes` directly, check it against the
   bulk flow above.
3. Optional: set `OMNITRON_URL` if you need to target a custom Omnitron host.
4. Optional: pass `filter_out_of_stock_products=True` to `insert_products`.
