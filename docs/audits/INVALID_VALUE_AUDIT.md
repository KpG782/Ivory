# Invalid Value Audit

## Purpose

This audit focuses specifically on invalid-value handling in the current Ivory setup.

It answers:

- which invalid inputs are already checked
- where those checks happen
- which cases were added to automated coverage
- what still remains weaker than ideal

## Main conclusion

Invalid values are now checked in two layers:

### Layer 1: field-entry coercion

This happens in:

- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

This layer catches:

- non-numeric input for `int` fields
- non-numeric input for `float` fields
- invalid boolean input for `yes/no` fields
- invalid enum values for constrained string fields
- off-topic or malformed free-text answers for key string fields

### Layer 2: quote validation before quote generation

This happens in:

- [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py)

This layer catches:

- future vehicle years
- negative accident counts
- invalid age ranges
- invalid year-built ranges
- invalid life ages
- invalid coverage amounts
- invalid term lengths

That means the system now rejects both:

- obviously malformed values at field-entry time
- semantically unreasonable values before quote generation

## What is now explicitly covered by tests

The backend integration suite now includes checks for:

### 1. Quote flow starts correctly

- `I want a quote`
- verifies transactional mode and identify step

### 2. Product selection moves into structured collection

- `home`
- verifies first real home field prompt appears

### 3. Off-topic string rejection

Example:

- during home quote `location`, user sends `what insurance products do you offer`

Expected and now tested:

- field is not stored
- same field is re-prompted
- quote mode is preserved

### 4. Invalid numeric type rejection

Example:

- vehicle year = `abc`

Expected and now tested:

- rejected immediately
- state does not advance

### 5. Future vehicle year rejection

Example:

- vehicle year = `2035`

Expected and now tested:

- accepted as an integer at entry
- rejected during validation before quote generation
- user is returned to `vehicle_year`

### 6. Invalid enum rejection

Example:

- home coverage level = `premium-plus`

Expected and now tested:

- rejected immediately
- same field remains active

### 7. Negative accident count rejection

Example:

- accidents = `-1`

Expected and now tested:

- accepted as an integer at entry
- rejected during validation before quote generation
- field is cleared and re-requested

### 8. Invalid boolean rejection

Example:

- smoker field = `sometimes`

Expected and now tested:

- rejected immediately
- user stays on smoker field

### 9. Invalid life term rejection

Example:

- term years = `15`

Expected and now tested:

- rejected immediately
- user stays on term field

## Important nuance

Not every invalid value is rejected at the same moment.

### Rejected immediately at collection time

Examples:

- `abc` for integer
- `sometimes` for yes/no
- `premium-plus` for coverage level
- off-topic policy question in a string field

### Rejected later during final quote validation

Examples:

- `2035` for vehicle year
- `-1` for accidents

These values are type-correct, so they pass coercion, but they are still blocked before quote generation.

This is acceptable for the current assessment setup, but it is important to understand the distinction.

## Current automated coverage result

Current backend test result after the invalid-value expansion:

- `25 passed`

Command used:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

## What still remains weaker

These areas are still lighter than ideal:

### 1. Free-text semantics

Fields such as:

- `vehicle_make`
- `vehicle_model`
- `location`

still rely on lightweight guardrails, not deep semantic validation.

That is acceptable for a take-home demo, but not production-grade.

### 2. More product-specific boundary cases

Still worth adding later:

- extremely old but technically numeric vehicle years
- unrealistic property values
- invalid but plausible location strings
- edge cases around life coverage amounts

### 3. UI-driven invalid-state tests

The backend is now tested more thoroughly than the browser interaction layer.

So the next invalid-value checks, if needed, should focus on browser behavior:

- does the UI display the rejection clearly
- does it keep the same pending field visible
- does it preserve the session snapshot correctly

## Practical conclusion

The current setup does now check invalid values properly in the backend.

More importantly, it now proves that:

- bad input does not silently advance state
- bad input does not produce a quote
- bad input can return the user to the correct field

That is a meaningful improvement over the earlier happy-path-only coverage.
