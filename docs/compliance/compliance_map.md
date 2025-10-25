# Карта Соответствия (Compliance Map) для ТЕ́ЛОС-Δ

**Внимание**: Этот файл является зеркалом основного документа в репозитории `SpaceCoreIskra-vOmega/docs/compliance/compliance_map.md`.

Он содержит ключевые требования и артефакты, связанные с:
1.  **EU AI Act** (для GPAI).
2.  **GPAI Code of Practice**.
3.  **NIST AI RMF** (Govern, Map, Measure, Manage).

**Ключевые артефакты в этом репозитории (`AgiAgentIskra`):**
*   **Traceability/Attribution**: `apps/rag/graphrag_manager.py` (GraphRAG logic)
*   **Governance/Gate**: `ops/canon_review/enforce.py` (Canon Review logic)
*   **Data/ETL Compliance**: `apps/etl/ingest_pipeline.py` (Checksums, Source URI)
*   **Infrastructure**: `ops/postgres/DDL_*.sql` (Data structure for compliance)

**См. также**: `../SpaceCoreIskra-vOmega/docs/compliance/compliance_map.md`

