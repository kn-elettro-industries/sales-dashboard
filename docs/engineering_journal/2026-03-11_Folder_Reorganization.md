# Engineering Log: 2026-03-11

## Feature: Folder Reorganization & Structure Cleanup

### Context
The project had accrued organizational debt: broken documentation links, mixed concerns (Python in assets), failing tests due to import paths, and inconsistent script naming. A systematic pass was needed to improve maintainability without affecting live deployments.

### Implementation

1.  **Documentation fixes**
    *   **Broken link**: README pointed to `docs/DEPLOY-NOW.md` (non-existent). Updated to `docs/DEPLOYMENT.md`.
    *   **Stale refs**: Removed references to `DEPLOY-TOMORROW.md` from README and STRUCTURE.md.

2.  **Shared Python package (`shared/`)**
    *   **Problem**: `assets/geo_data.py` lived alongside logos and CSS. Geo data is shared Python logic used by backend (routes) and legacy (advanced analytics).
    *   **Solution**: Created `shared/` at repo root. Moved `geo_data.py` there. Updated imports in `backend/api/routes.py` and `legacy/analytics/advanced.py` from `assets.geo_data` → `shared.geo_data`.
    *   **Docker**: Both `backend/Dockerfile` and `legacy/Dockerfile` now `COPY shared/` into the image so deployed apps resolve the module.

3.  **Test imports**
    *   **Problem**: `tests/test_etl.py` imported `from etl_pipeline` as if it lived at repo root. Actual location: `legacy/etl_pipeline.py`.
    *   **Solution**: Added `legacy/__init__.py` to make legacy a proper package. Updated test to `from legacy.etl_pipeline import standardize, calculate_taxes, merge_customer_master` with repo root in `sys.path`.

4.  **Script naming**
    *   **Inconsistency**: `start_backend.bat` used snake_case while others used PascalCase (`Run_App.bat`, `Setup_App.bat`).
    *   **Solution**: Renamed `start_backend.bat` → `Start_Backend.bat`.

5.  **STRUCTURE.md**
    *   Documented `shared/`. Aligned Paths section with actual files.

### Outcomes
| Item | Benefit |
|------|---------|
| Shared code | Clear home for backend/legacy cross-cutting logic |
| Tests | ETL suite runs without import errors |
| Docs | Deploy link works; no broken references |
| Scripts | Consistent naming across batch helpers |

### Technical Notes
*   **Live impact**: None until push + redeploy. Dockerfiles updated so future deploys include `shared/`; no downtime or config changes required.
*   **Path setup**: `routes.py` already inserts repo root into `sys.path` before geo import; `shared` is found when repo root is in path (local dev) or when `/app` contains `shared/` (Docker).
*   **Legacy Docker**: Workdir is `/app`; `COPY shared/ /app/shared/` ensures `import shared.geo_data` resolves when Streamlit runs from `/app`.
