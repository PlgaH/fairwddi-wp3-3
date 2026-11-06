# FAIRwDDI `COMPARE` Report — `compare-batch-3-cee551`

## Overview

- **Stage:** `compare`
- **Job ID:** `compare-batch-3-cee551`
- **Created At:** `2026-11-06T19:43:02.734449+00:00`
- **Review Gate Status:** **READY (No Review Needed)**
- **Errors:** `0` | **Warnings:** `0` | **Pending Review Items:** `0`
- **Source File:** `fr.cdsp.ddi.elipss.2015.ddic.ddi40.json`
- **Detected Format:** `ddi-l:4.0:json`
- **Ingest Batch ID:** `#3`

## Summary Metrics

| Metric | Value |
| :--- | :--- |
| `total_candidates` | `63` |
| `threshold` | `0.75` |
| `by_match_type` | `{'FACET_EXACT': 63}` |
| `by_resource_type` | `{'CodeList': 63}` |

## Cross-Survey Deduplication (URN Aliases)

> [!TIP]
> **63 incoming entities** match pre-existing canonical resources in PostgreSQL (**CodeList:** 63). Instead of inserting duplicate database records, the engine will link these resources to existing canonical URNs via `URNAlias` records, ensuring multi-study harmonization and zero database bloat.

| Type | Source URN (Incoming) | Target Canonical URN | Match Basis |
| :--- | :--- | :--- | :--- |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V107:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V98:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V117:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V108:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V118:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V109:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V119:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V110:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V136:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V127:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V137:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V128:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V138:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V129:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V140:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V131:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V141:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V132:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V142:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V133:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V144:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V135:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V145:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V136:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V154:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V145:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V155:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V146:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V157:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V148:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V158:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V149:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V160:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V151:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V161:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V152:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V168:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V156:3.0.0` | FACET_EXACT match (confidence=0.95) |
| `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V179:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V167:3.0.0` | FACET_EXACT match (confidence=0.95) |
| *...* | *(43 additional `CodeList` aliases omitted)* | | |

## Planned Actions (63 total)

| ID | Action | Resource Type | Source URN | Target URN | Conf | Review? |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `cmp-0001` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V107:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V98:3.0.0` | 0.95 | No |
| `cmp-0002` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V117:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V108:3.0.0` | 0.95 | No |
| `cmp-0003` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V118:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V109:3.0.0` | 0.95 | No |
| `cmp-0004` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V119:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V110:3.0.0` | 0.95 | No |
| `cmp-0005` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V136:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V127:3.0.0` | 0.95 | No |
| `cmp-0006` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V137:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V128:3.0.0` | 0.95 | No |
| `cmp-0007` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V138:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V129:3.0.0` | 0.95 | No |
| `cmp-0008` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V140:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V131:3.0.0` | 0.95 | No |
| `cmp-0009` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V141:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V132:3.0.0` | 0.95 | No |
| `cmp-0010` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V142:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V133:3.0.0` | 0.95 | No |
| `cmp-0011` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V144:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V135:3.0.0` | 0.95 | No |
| `cmp-0012` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V145:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V136:3.0.0` | 0.95 | No |
| `cmp-0013` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V154:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V145:3.0.0` | 0.95 | No |
| `cmp-0014` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V155:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V146:3.0.0` | 0.95 | No |
| `cmp-0015` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V157:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V148:3.0.0` | 0.95 | No |
| `cmp-0016` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V158:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V149:3.0.0` | 0.95 | No |
| `cmp-0017` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V160:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V151:3.0.0` | 0.95 | No |
| `cmp-0018` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V161:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V152:3.0.0` | 0.95 | No |
| `cmp-0019` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V168:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V156:3.0.0` | 0.95 | No |
| `cmp-0020` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V179:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V167:3.0.0` | 0.95 | No |
| `cmp-0021` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V180:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V168:3.0.0` | 0.95 | No |
| `cmp-0022` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V181:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V169:3.0.0` | 0.95 | No |
| `cmp-0023` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V182:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V170:3.0.0` | 0.95 | No |
| `cmp-0024` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V183:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V171:3.0.0` | 0.95 | No |
| `cmp-0025` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V193:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V175:3.0.0` | 0.95 | No |
| `cmp-0026` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V193:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V180:3.0.0` | 0.95 | No |
| `cmp-0027` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V194:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V176:3.0.0` | 0.95 | No |
| `cmp-0028` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V194:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V181:3.0.0` | 0.95 | No |
| `cmp-0029` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V195:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V177:3.0.0` | 0.95 | No |
| `cmp-0030` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V195:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V182:3.0.0` | 0.95 | No |
| `cmp-0031` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V196:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V178:3.0.0` | 0.95 | No |
| `cmp-0032` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V196:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V183:3.0.0` | 0.95 | No |
| `cmp-0033` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V198:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V180:3.0.0` | 0.95 | No |
| `cmp-0034` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V198:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V185:3.0.0` | 0.95 | No |
| `cmp-0035` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V199:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V181:3.0.0` | 0.95 | No |
| `cmp-0036` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V199:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V186:3.0.0` | 0.95 | No |
| `cmp-0037` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V200:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V182:3.0.0` | 0.95 | No |
| `cmp-0038` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V200:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V187:3.0.0` | 0.95 | No |
| `cmp-0039` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V201:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V183:3.0.0` | 0.95 | No |
| `cmp-0040` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V201:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V188:3.0.0` | 0.95 | No |
| `cmp-0041` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V202:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V184:3.0.0` | 0.95 | No |
| `cmp-0042` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V202:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V189:3.0.0` | 0.95 | No |
| `cmp-0043` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V203:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2013.04.ea-codelists.cl_V185:3.0.0` | 0.95 | No |
| `cmp-0044` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V203:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V190:3.0.0` | 0.95 | No |
| `cmp-0045` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V26:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V78:3.0.0` | 0.95 | No |
| `cmp-0046` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V27:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V20:3.0.0` | 0.95 | No |
| `cmp-0047` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V31:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V24:3.0.0` | 0.95 | No |
| `cmp-0048` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V33:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V26:3.0.0` | 0.95 | No |
| `cmp-0049` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V34:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V27:3.0.0` | 0.95 | No |
| `cmp-0050` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V44:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V37:3.0.0` | 0.95 | No |
| `cmp-0051` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V45:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V38:3.0.0` | 0.95 | No |
| `cmp-0052` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V46:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V39:3.0.0` | 0.95 | No |
| `cmp-0053` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V52:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V45:3.0.0` | 0.95 | No |
| `cmp-0054` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V53:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V46:3.0.0` | 0.95 | No |
| `cmp-0055` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V56:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V49:3.0.0` | 0.95 | No |
| `cmp-0056` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V57:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V50:3.0.0` | 0.95 | No |
| `cmp-0057` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V83:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V74:3.0.0` | 0.95 | No |
| `cmp-0058` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V84:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V75:3.0.0` | 0.95 | No |
| `cmp-0059` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V85:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V76:3.0.0` | 0.95 | No |
| `cmp-0060` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V90:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V81:3.0.0` | 0.95 | No |
| `cmp-0061` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V92:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V83:3.0.0` | 0.95 | No |
| `cmp-0062` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V93:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V84:3.0.0` | 0.95 | No |
| `cmp-0063` | `alias` | `CodeList` | `urn:ddi:fr.cdsp:fr.cdsp.ddi.elipss.2015.03.ea-codelists.cl_V96:3.0.0` | `urn:ddi:fr.cdsp:fr.cdsp.elipss.ddi.2014.03.ea-codelists.cl_V87:3.0.0` | 0.95 | No |
