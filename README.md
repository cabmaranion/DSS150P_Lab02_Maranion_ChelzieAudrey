# DSS150P Weeks 2-3 Laboratory

**Name:** Chelzie Audrey Maranion
**Student Number:** 2024108712

## Quick start
1. `python -m venv .venv`
2. Activate `.venv`
3. `pip install -r requirements.txt`
4. `docker compose up -d`
5. Load PostgreSQL seed: `Get-Content sql\seed_support_tickets.sql | docker exec -i dss150p-lab2-postgres psql -U dss150p -d dss150p`
6. Terminal A: `python src/local_api_server.py`
7. Terminal B: `python src/ingest_pipeline.py` then `python src/validate_raw.py`

## Deliverables
- `docs/profiling_report.md` — source profiling report
- `docs/logical_schema.md` — logical schema for customers and API events
- `docs/ingestion_design.md` — ingestion design and CDC discussion
- `docs/watermark_semantics.md` — watermark failure modes and mitigations
- `docs/reflection.md` — engineering reflection
- `config/source_metadata.yml` — metadata for all five sources
- `config/data_contract_customers.yml` — customers data contract
- `docs/evidence/` — run log and validation output

## Notes
- The lab guide and the starter README both refer to the Postgres container as `dss150p-w23-postgres`, but `docker-compose.yml` names it `dss150p-lab2-postgres`. The compose file is authoritative and that name is used throughout.
- PowerShell does not support `<` for input redirection, so `Get-Content ... | docker exec -i` is used instead of the `<` form shown in the guide.
- `raw/` and `state/` are gitignored per the starter README. The run log and validation output are copied to `docs/evidence/` so results are visible in the repository.

## AI Usage

**Tool used:** Claude (Anthropic)

**What I asked it to help with:**
- Writing the implementation code in `src/profile_sources.py`, `src/ingest_pipeline.py`, and `src/validate_raw.py`
- Explaining PowerShell syntax differences (here-strings, `-i` vs `-it` with docker exec, execution policy) and diagnosing errors as they came up
- Identifying that the lab guide and starter README name the Postgres container differently from `docker-compose.yml`
- Help in structuring the profiling report, metadata inventory, logical schema, data contract, and ingestion design
- Reviewing my draft answers and reasoning, and flagging where a claim did not match what the profiling actually showed

**What I did and verified myself:**
- Ran every command and script on my own machine and checked the output at each step
- All counts, hashes, dtypes, and watermark values in the documentation come from actual runs, not generated examples
- Investigated the C0090 duplicate myself and determined it maps to two different people
- Wrote the validation rules, the nested-object representation options, the format comparison reasoning, the CDC strategy, the watermark analysis, and all ten reflection answers in my own words
- Demonstrated the failure experiment and confirmed the watermark did not advance