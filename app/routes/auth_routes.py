from fastapi import APIRouter, HTTPException
from app.schemas.user_schema import UserSignup, UserLogin
from app.db.supabase import supabase
router = APIRouter(prefix="/auth", tags=["Auth"])
from fastapi import HTTPException
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/signup")
def signup(user: UserSignup):
    try:
        if user.password != user.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        if not user.email or not EMAIL_REGEX.match(user.email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        if len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        auth_res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        print("AUTH RESPONSE:", auth_res)

        if not auth_res or auth_res.user is None:
            raise HTTPException(
                status_code=400,
                detail="User already exists or signup blocked (rate limit)"
            )

        user_id = auth_res.user.id

        db_res = supabase.table("user").insert({
            "id": user_id, 
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "role": "citizen"
        }).execute()

        print("DB RESPONSE:", db_res)

        return {
            "msg": "Citizen registered successfully",
            "user": {
                "id": user_id,
                "email": user.email,
                "name": user.name,
                "role": "citizen"
            }
        }

    except HTTPException as e:
        raise e  

    except Exception as e:
        error_msg = str(e)
        print("SIGNUP ERROR:", error_msg)

        if "User already registered" in error_msg:
            raise HTTPException(status_code=400, detail="Email already registered")

        if "rate limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later")

        raise HTTPException(status_code=400, detail="Signup failed. Please try again")


@router.post("/login")
def login(user: UserLogin):

    res = supabase.auth.sign_in_with_password({
        "email": user.email,
        "password": user.password
    })

    if res.user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # check role from DB
    db_user = supabase.table("user").select("*").eq("email", user.email).single().execute()

    if not db_user.data:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.data["role"] != user.role:
        raise HTTPException(status_code=403, detail="Role mismatch")

    return {
        "msg": "Login successful",
        "user": db_user.data,
        "session": res.session
    }