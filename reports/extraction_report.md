# PDF Ingestion and Text Extraction Report

**Extraction Timestamp:** 2026-10-17T12:31:47.941814
**Total Documents:** 10
**Successful / Cached:** 10
**Partial / Scanned:** 0
**Failed:** 0
**Total Extracted Characters:** 1,980,658

## Document Extraction Summary

| Filename | Status | Pages | Characters | Zero-Text Pages | OCR Flagged Pages |
| --- | --- | --- | --- | --- | --- |
| `0ANREPORT201718077745EC9A874DB38C991F580ED14242.pdf` | **CACHED_SUCCESS** | 268 | 839,857 | 0 | 2 |
| `Credit information.pdf` | **CACHED_SUCCESS** | 50 | 89,738 | 0 | 0 |
| `Cyber security.pdf` | **CACHED_SUCCESS** | 56 | 100,780 | 0 | 0 |
| `Demonitization.pdf` | **CACHED_SUCCESS** | 59 | 130,731 | 0 | 0 |
| `fatf-recommendations last updated june 2026.pdf` | **CACHED_SUCCESS** | 151 | 371,766 | 0 | 0 |
| `Interest rates.pdf` | **CACHED_SUCCESS** | 25 | 45,325 | 0 | 0 |
| `kyc.pdf` | **CACHED_SUCCESS** | 101 | 203,608 | 0 | 0 |
| `Operational guidelines.pdf` | **CACHED_SUCCESS** | 70 | 130,718 | 0 | 0 |
| `Supervisory Credit.pdf` | **CACHED_SUCCESS** | 5 | 6,454 | 0 | 0 |
| `WP-450-Pratap-Singh_2-Final.pdf` | **CACHED_SUCCESS** | 22 | 61,681 | 0 | 0 |

## Observations & Regulatory Extraction Insights
- All 10 documents were successfully parsed with PyMuPDF text streams.
- No documents require heavy OCR for core textual analysis.
- Per-document structured JSON files have been generated under `data/processed/{doc_id}.json`.
- Page numbers, character offsets, headings, and metadata are cleanly preserved.