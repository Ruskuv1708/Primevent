from fastapi import FastAPI
from contextlib import asynccontextmanager 
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from dotenv import load_dotenv

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- IMPORTS: SYSTEM CORE ---
from core.database_connector import engine, Base, SessionLocal
from core.middleware import WorkspaceMiddleware
from core.config import settings
from core.schema_sync import ensure_runtime_schema

# --- IMPORTS: MODULE ROUTERS ---
from modules.access_control.router import router as access_router

from modules.dynamic_records.router import router as dynamic_router
from modules.workflow.router import router as workflow_router
from modules.notifications.router import router as notif_router
from modules.file_storage.router import router as file_router
from modules.reports.router import router as report_router
from modules.workspace_management.router import router as workspace_router, apply_saved_ai_settings
from modules.registry.router import router as registry_router
from modules.module_registry.router import router as module_router
from modules.ai_architect.router import router as ai_architect_router
from modules.animator_schedule.router import router as animator_schedule_router
from modules.employee_evaluations.router import router as employee_evaluations_router

# --- IMPORTS: MODELS (For Table Creation) ---
from modules.access_control.models import User
from modules.access_control.models import Workspace  # ✅ NEW
from modules.dynamic_records.models import FormTemplate, FormRecord
from modules.workflow.models import Department, Request
from modules.notifications.models import Notification
from modules.file_storage.models import FileAttachment
from modules.registry.models import Company, Client, ClientObject
from modules.animator_schedule.models import AnimatorBooking, AnimatorUnavailability
from modules.employee_evaluations.models import EmployeeEvaluation
from modules.ai_architect.models import (
    AIConversation,
    AIConversationMessage,
    AIBusinessBlueprint,
    AIChangeEvent,
    AIChangeProposal,
)

# --- LIFESPAN MANAGER (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. STARTUP
    print("------------------------------------------------")
    print("⚡ SYSTEM STARTUP: Initiating...")
    try:
        # Check Database Connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ DATABASE: Connected")
        
        # Create Tables (Dev/Local only)
        if settings.AUTO_CREATE_TABLES:
            print("🔨 MIGRATION: Checking tables...")
            Base.metadata.create_all(bind=engine)
            added_columns = ensure_runtime_schema(engine)
            if added_columns:
                print(f"✅ MIGRATION: Runtime columns verified: {', '.join(added_columns)}")
            else:
                print("✅ MIGRATION: Runtime columns verified; no drift found")
            print("✅ MIGRATION: Tables synced successfully")
        else:
            print("ℹ️  AUTO_CREATE_TABLES disabled; skipping create_all()")

        try:
            db = SessionLocal()
            try:
                if apply_saved_ai_settings(db):
                    print("✅ AI ARCHITECT: Stored provider settings loaded")
                else:
                    print("ℹ️  AI ARCHITECT: Using environment provider settings")
            finally:
                db.close()
        except Exception as settings_error:
            print(f"⚠️  AI ARCHITECT: Stored provider settings not loaded: {settings_error}")
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
    print("------------------------------------------------")
    
    yield
    
    # 2. SHUTDOWN
    print("------------------------------------------------")
    print("🛑 SYSTEM SHUTDOWN")
    print("------------------------------------------------")

# --- APP INITIALIZATION ---
crm_core_app = FastAPI(title="Modular CRM Platform", lifespan=lifespan)

# --- CORS ---
if settings.CORS_ORIGINS:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
	"http://100.71.60.13:3000",
   	"http://localhost:3000",
    ]
crm_core_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PROXY / HOST CONTROLS ---
if settings.TRUSTED_PROXY_HOSTS:
    proxy_hosts = [h.strip() for h in settings.TRUSTED_PROXY_HOSTS.split(",") if h.strip()]
    crm_core_app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=proxy_hosts)

if settings.ALLOWED_HOSTS:
    allowed_hosts = [h.strip() for h in settings.ALLOWED_HOSTS.split(",") if h.strip()]
    crm_core_app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# --- WORKSPACE MIDDLEWARE ---
crm_core_app.add_middleware(WorkspaceMiddleware)

# --- REGISTER MODULES ---
crm_core_app.include_router(workspace_router)  # ✅ Register Workspace Management FIRST (highest priority)
crm_core_app.include_router(access_router)
crm_core_app.include_router(dynamic_router)
crm_core_app.include_router(workflow_router)
crm_core_app.include_router(notif_router)
crm_core_app.include_router(file_router)
crm_core_app.include_router(report_router)
crm_core_app.include_router(registry_router)
crm_core_app.include_router(module_router)
crm_core_app.include_router(ai_architect_router)
crm_core_app.include_router(animator_schedule_router)
crm_core_app.include_router(employee_evaluations_router)

# --- HEALTH CHECK ---
@crm_core_app.get("/")
def report_system_status():
    return {"status": "online"}
