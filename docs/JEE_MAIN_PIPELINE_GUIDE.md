# JEE Main question extraction rules

This version is tuned against the supplied 8-page JEE Main sample structure:

- Page 1 = instructions/metadata; no question crops should start here.
- Section I Physics = Q1-Q25.
- Section II Chemistry = Q26-Q50.
- Section III Mathematics = Q51-Q75.
- Objective questions are one crop containing the stem + all four options.
- Integer-type questions are one crop containing the complete numerical question.
- Formal `SECTION-I/II/III` headers override page-1 `Topic Covered` metadata.
- PDF text blocks such as `1.` + `Find ...` are joined before question detection.
- Two-column pages are handled by logical question number for detection and same-column geometry for crop boundaries.

## Important architecture rule

Do **not** detect `(1)`, `(2)`, `(3)`, `(4)` as question starts. They are option labels.

For this sample, question detection is number-driven because the PDF visually interleaves columns: e.g. Q26 begins lower in the left column while Q20-Q25 are in the right column. Crop termination is still same-column based, so Q25 does not accidentally consume the Chemistry section.
