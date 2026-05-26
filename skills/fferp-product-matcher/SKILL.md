---
name: fferp-product-matcher
description: Match customer product names from WhatsApp, Excel, PDFs, or free text to internal FFERP SKUs with confidence scores and review flags. Use when Codex needs SKU matching, alias matching, fuzzy product lookup, unmatched-product review files, or product-confidence validation.
---

# FFERP Product Matcher

## Workflow

1. Load product master data from `data/master/products.csv`, `products.xlsx`, or a user-specified file.
2. Build candidate names from SKU, product name, aliases, category, package size, and unit.
3. Match each raw customer product phrase to a SKU using exact, alias, and fuzzy matching.
4. Set `needs_review=true` when confidence is below `0.85`, multiple candidates are close, or package/unit is ambiguous.
5. Write unmatched names to an explicit review output.
6. Return structured matches and append an action log entry.

## Safety Rules

- Never silently guess product identity.
- Do not convert a raw product phrase into an official SKU below the confidence threshold.
- Preserve the original customer wording.
- Do not update product master data without a separate approval task.

## Outputs

- matched SKU candidates
- confidence score
- `needs_review` flag
- unmatched product review file

## Resource Map

- Use `schemas/product_match.schema.json` for output shape.
- Use `templates/product_review.md` for review summaries.
