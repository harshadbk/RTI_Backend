from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.user_schema import UserSignup, UserLogin
from app.db.supabase import supabase
import re

router = APIRouter(prefix="/auth", tags=["Auth"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ✅ Runs AFTER response is sent — user doesn't wait!
def insert_user_db(user_id, email, name, phone):
    try:
        supabase.table("users").insert({
            "id": user_id,
            "email": email,
            "name": name,
            "phone": phone,
            "role": "citizen"
        }).execute()
        print("DB INSERT SUCCESS ✅")
    except Exception as e:
        print("DB INSERT ERROR:", str(e))


@router.post("/signup")
async def signup(user: UserSignup, background_tasks: BackgroundTasks):
    try:
        # ✅ Validate first before any network call
        if user.password != user.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        if not user.email or not EMAIL_REGEX.match(user.email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        if len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        # ✅ Single auth call with metadata — removed extra DB check before signup
        auth_res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "role": "citizen",   # ✅ stored in metadata
                    "name": user.name,   # ✅ stored in metadata
                    "phone": user.phone  # ✅ stored in metadata
                }
            }
        })

        if not auth_res or auth_res.user is None:
            raise HTTPException(status_code=400, detail="Signup failed. Try again.")

        user_id = auth_res.user.id

        # ✅ DB insert runs in background — response sent immediately!
        background_tasks.add_task(
            insert_user_db,
            user_id,
            user.email,
            user.name,
            user.phone
        )

        # ✅ Returned immediately without waiting for DB insert
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

        metadata = res.user.user_metadata
        db_user = res.data
        if hasattr(user, "role") and user.role and db_user["role"] != user.role:
            raise HTTPException(status_code=403, detail="Role mismatch")

        return {
            "msg": "Login successful",
            "user": {
                "id": res.user.id,
                "email": res.user.email,
                "name": metadata.get("name"),
                "phone": metadata.get("phone"),
                "role": metadata.get("role")
            },
            "session": res.session
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print("LOGIN ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))