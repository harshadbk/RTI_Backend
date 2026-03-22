from fastapi import APIRouter, HTTPException
from app.schemas.user_schema import UserSignup, UserLogin
from app.db.supabase import supabase
import re

router = APIRouter(prefix="/auth", tags=["Auth"])

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

        try:
            existing_user = supabase.table("users") \
                .select("id") \
                .filter("email", "eq", user.email) \
                .execute()

            if existing_user.data and len(existing_user.data) > 0:
                raise HTTPException(status_code=400, detail="Email already registered")

        except HTTPException as e:
            raise e
        except Exception:
            pass  

        auth_res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        print("AUTH RESPONSE USER:", auth_res.user)

        if not auth_res or auth_res.user is None:
            raise HTTPException(status_code=400, detail="Signup failed. Try again.")

        user_id = auth_res.user.id

        try:
            db_res = supabase.table("users").insert({
                "id": user_id,
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "role": "citizen"
            }).execute()

            print("DB INSERT RESPONSE:", db_res)

            print("DB INSERT SUCCESS ✅")

        except Exception as db_err:
            error_msg = str(db_err)
            print("DB INSERT ERROR:", error_msg)

            if "23505" in error_msg or "duplicate" in error_msg.lower():
                raise HTTPException(status_code=400, detail="Email already registered")

            if "Expecting value" in error_msg:
               print("Insert likely succeeded (empty response is OK) ✅")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Profile save failed: {error_msg}"
                )

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