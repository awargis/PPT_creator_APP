# Verification Record

## Answer-key robustness update — 2026-09-20

The answer-key parser was hardened without changing the PDF question detection, cropping, enhancement, subject classification, or PPT generation architecture.

### Accepted answer-key styles

- `1: A, 2: B, 3: C`
- `1: (4), 2: (4), 3: (2)`
- Same entries in any order, e.g. `75:(1.00), 12:(3), 1:(4), ...`
- `Q1-A`, `Q2-B`
- `Question 1: (4)` / `Ans 1: (4)`
- `1) (4)`, `1. (4)`, `1 -> (4)`, `1 = (4)`, `1 - (4)`
- `[1] (4)`
- `1 A` / `1 (4)` and compact whitespace-separated keys
- Integer, decimal, negative, fraction, and slash-separated answers

Parentheses are normalized away: `(1.00)` becomes `1.00`.

### Automated verification

- `PYTHONPATH=. python -m pytest -q` → **23 passed**
- Exact supplied 75-answer JEE Main key → **75/75 parsed**
- Shuffled-order key → **all question numbers mapped independently of order**
- Full PDF integration → **75/75 regions received the correct answer**
- Manifest → **75/75 answers mapped**
- Physics PPT → **25 slides**
- Chemistry PPT → **25 slides**
- Mathematics PPT → **25 slides**

The existing question detection/cropping and PPT functionality was not otherwise changed.
