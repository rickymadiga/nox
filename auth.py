from fastapi import APIRouter, HTTPException

router = APIRouter()   # ✅ THIS LINE IS REQUIRED

# Example routes
@router.post("/signup")
def signup(data: dict):
    return {"message": "Signup works"}

@router.post("/login")
def login(data: dict):
    return {"token": "fake-token"}