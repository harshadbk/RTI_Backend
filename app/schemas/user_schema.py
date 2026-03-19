from pydantic import BaseModel, EmailStr

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: str 