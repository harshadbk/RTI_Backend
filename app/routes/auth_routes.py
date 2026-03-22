from fastapi import APIRouter, HTTPException
from app.schemas.user_schema import UserSignup, UserLogin
from app.db.supabase import supabase
import re

router = APIRouter(prefix="/auth", tags=["Auth"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@router.post("/signup")
async def signup(user: UserSignup):
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

        if not auth_res or auth_res.user is None:
            raise HTTPException(status_code=400, detail="Signup failed. Try again.")

        user_id = auth_res.user.id

        supabase.table("users").insert({
            "id": user_id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "role": "citizen"
        }).execute()

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

        if "User already registered" in error_msg or "23505" in error_msg:
            raise HTTPException(status_code=400, detail="Email already registered")

        if "rate limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later")

        raise HTTPException(status_code=400, detail=f"Signup failed: {error_msg}")


@router.post("/login")
async def login(user: UserLogin):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })

        if res.user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        db_response = supabase.table("users") \
            .select("id, email, name, phone, role") \
            .eq("id", res.user.id) \                   
            .single() \                               
            .execute()

        if not db_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        db_user = db_response.data

        if hasattr(user, "role") and user.role and db_user["role"] != user.role:
            raise HTTPException(status_code=403, detail="Role mismatch")

        return {
            "msg": "Login successful",
            "user": db_user,
            "session": res.session
        }

    except HTTPException as e:
        raise e

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))