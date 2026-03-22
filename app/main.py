import os
import time
import uvicorn
from fastapi import FastAPI, Request  
from app.routes.auth_routes import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    return {"message": "API running "}

# This runs on EVERY request automatically
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    end_time = time.time()
    duration = (end_time - start_time) * 1000
    
    print(f"{request.method} {request.url.path} → {duration:.2f}ms")
    
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)