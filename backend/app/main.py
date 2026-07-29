from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine
from app.routers import verify, verifications

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Verifio KYC Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(verify.router)
app.include_router(verifications.router)


@app.get("/health")
def health():
    return {"status": "ok"}
