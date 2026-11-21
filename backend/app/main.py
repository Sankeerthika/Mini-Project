from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, admin as admin_router, manager as manager_router, employee as employee_router, meetings as meetings_router


def create_tables_safe():
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("[DB] Tables created/verified successfully")
    except Exception as e:
        print(f"[DB WARNING] Could not initialize database tables: {type(e).__name__}: {e}")
        print("       Tables will be initialized on first successful DB connection.")
        print("       Ensure PostgreSQL is running and credentials in .env are correct.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables_safe()
    yield


app = FastAPI(
    title="AI Meeting Intelligence & Commitment Tracking API",
    description="API for managing meetings, AI analysis, and task tracking",
    version="0.1.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin_router.router)
app.include_router(manager_router.router)
app.include_router(employee_router.router)
app.include_router(meetings_router.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "AI Meeting Intelligence API is running"}
