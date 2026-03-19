from pydantic import BaseModel, EmailStr

# Signup (ONLY CITIZEN)
class UserSignup(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str


# Login (ALL ROLES)
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: str   # citizen / pio / authority