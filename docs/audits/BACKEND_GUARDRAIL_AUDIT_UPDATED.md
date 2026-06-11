# Backend Guardrail Audit Updated

## Summary

This audit was run after the latest backend strictness update focused on:

- validation-before-commit
- stricter location guardrails
- realistic home property value constraints
- immediate year-built rejection

The core workflow integrity bug you identified is now fixed.

## Main finding

The backend now follows the correct transactional invariant:

1. read the current field
2. validate the submitted value for that field
3. only if valid, commit it to state
4. then advance to the next field

It no longer advances optimistically and rejects the previous field later.

## What was wrong before

Previously, the risky pattern was:

- accept the current value
- move to the next field
- only later discover that the previous field was invalid

That caused:

- delayed error messages
- confusing UX
- quote summaries built from weak or unrealistic values

## What is fixed now

### 1. `zoo` no longer passes as a location

Re-check result:

- `zoo` is rejected
- `current_field` stays `location`
- state does not advance

Current response style:

`Please enter a real city or location, for example Makati, Manila, or Quezon City. Which city or location is the property in?`

### 2. `100` no longer advances home property value collection

Re-check result:

- `100` is rejected immediately for `estimated_value`
- `current_field` stays `estimated_value`
- state does not advance

Current response style:

`Please enter a more realistic property value in USD, for example 100000 or 350000. What is the estimated property value in USD? (e.g. 350000)`

### 3. `year_built = 100` is rejected before coverage-level advance

Re-check result:

- `100` is rejected immediately for `year_built`
- `current_field` stays `year_built`
- the bot does **not** ask for coverage level yet

Current response style:

`Year built must be between 1801 and 2026. What year was the property built?`

### 4. Valid continuation still works

After valid inputs:

- `Makati`
- `350000`
- `2024`
- `basic`

the flow continues cleanly and generates the quote.

## What was changed in code

Primary changes were made in:

- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

Key updates:

- field specs now support stricter numeric ranges at collection time
- `vehicle_year`, `driver_age`, `age`, and `year_built` use immediate min/max validation
- `estimated_value` now uses a realistic minimum instead of only `> 0`
- `location` now has a denylist and stronger formatting checks

## Verified replay

The following replay now behaves correctly:

```text
I want a quote
home
house
zoo
Makati
100
350000
100
2024
basic
```

Observed result:

- `zoo` rejected
- `100` property value rejected
- `100` year built rejected
- no premature advance to coverage level
- valid path completes and generates a quote

## Automated verification

Backend tests now pass with the expanded guardrail coverage.

Command:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

Result:

- `31 passed`

## What this means now

The backend is in a significantly better state for demo use.

Most importantly:

- invalid values are no longer being committed before validation
- state progression is now much more trustworthy
- quote summaries are less likely to contain obviously bad business data from weak inputs

## Remaining minor note

The only recurring verification noise left is:

- pytest cache permission warning in this workspace

That is not a backend logic problem.

## Final verdict

The main workflow integrity problem described in the audit is now fixed.

The backend is now much closer to a strong demo-safe state because it validates current-field input before commit and before state advance.
