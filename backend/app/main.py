from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.schemas import ScanRequest, Scan
from app.core.engine import run_scan
from app.api.llm import router as llm_router  # <-- add

app = FastAPI(title="Hack Anything API", version="0.3.0")

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

_LAST_SCAN: Scan | None = None

@app.post("/scan", response_model=Scan)
async def start_scan(req: ScanRequest):
    global _LAST_SCAN
    _LAST_SCAN = await run_scan(str(req.url))
    return _LAST_SCAN

@app.get("/scan/{scan_id}", response_model=Scan | None)
async def get_scan(scan_id: str):
    return _LAST_SCAN

# mount the chat router
app.include_router(llm_router)
