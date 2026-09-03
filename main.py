from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import db
from pydantic import BaseModel
import psycopg2
from datetime import date
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import llm
from slowapi import Limiter,_rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

load_dotenv()



SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

class Property(BaseModel):
    id: int
    name: str
    address: str
    city: str
    square_ft: int
    floors: int | None
    market_value: int

class PropertyCreate(BaseModel):
    name:str
    address:str
    city:str
    square_ft: int
    floors: int | None
    market_value: int

class CreateLeases(BaseModel):
    tenant_name: str
    start_date: date
    end_date: date
    monthly_rent: int
    leased_sqft: int

class Lease(CreateLeases):
    id: int

class Signup(BaseModel):
    username: str
    password: str

class AskRequest(BaseModel):
    question: str


def create_token(username):
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore

def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    token = auth.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]



@app.post("/signup")
def signup(user: Signup):
    hashed = pwd_context.hash(user.password)
    return db.create_user(user.username, hashed)


@app.post("/login")
def login(user:Signup):
    row = db.get_user_by_username(user.username)
    if row is None or not pwd_context.verify(user.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_token(user.username)}


@app.post("/ask")
@limiter.limit("5/minute")
def ask(request: Request, body: AskRequest, current_user: str = Depends(get_current_user)):
    data = db.occupancy()
    return {"answer": llm.ask_about_portfolio(body.question, data)}
    
@app.get("/properties/expiring_leases")
def expiring_leases(days: int = 90, current_user: str = Depends(get_current_user)):
    return db.expiring_leases(days)


@app.get("/properties/occupancy")
def calculate_occupancy(current_user: str = Depends(get_current_user)):
    rows = db.occupancy()
    if rows is None:
        raise HTTPException(status_code=404, detail="Not enough data")
    return rows

@app.get("/properties/{property_id}")
def get_property(property_id:int, current_user: str = Depends(get_current_user)):
    row = db.get_property(property_id)
    if row is None:
        raise HTTPException(status_code=404,detail="Property not found")
    return row

@app.post("/properties",response_model=Property)
def create_property(prop:PropertyCreate, current_user: str = Depends(get_current_user)):
    row =  db.create_property(prop)
    llm.clear_cache()
    return row


@app.get("/properties", response_model=list[Property])
def get_all_properties(city: str | None = None, current_user: str = Depends(get_current_user)):
    if city is None:
        return db.get_properties()
    return db.get_property_by_city(city)


@app.get("/properties/{property_id}/leases")
def get_lease(property_id: int, current_user: str = Depends(get_current_user)):
    if db.get_property(property_id) is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db.get_lease(property_id)

@app.get("/leases")
def get_all_leases(current_user: str = Depends(get_current_user)):
    rows = db.get_all_leases()
    if rows is None:
        raise HTTPException(status_code = 404, detail = "No leases found")
    return rows

@app.post("/properties/{property_id}/leases",response_model=Lease)
def create_lease(property_id: int, leases:CreateLeases, current_user: str = Depends(get_current_user)):
    row = db.create_leases(property_id,leases)
    llm.clear_cache()
    return row

@app.delete("/leases/{lease_id}")
def delete_lease(lease_id: int, current_user: str = Depends(get_current_user)):
    row = db.delete_lease(lease_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Lease not found")
    llm.clear_cache()
    return row

@app.delete("/properties/{property_id}")
def delete_property(property_id: int, current_user: str = Depends(get_current_user)):
    try:
        row = db.delete_property(property_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status_code=409, detail="Cannot delete a property that has a lease attached to it.")
    if row is None:
        raise HTTPException(status_code=404, detail="Property not found")
    llm.clear_cache()
    return row

@app.get("/properties/{property_id}/revenue")
def calculate_revenue(property_id:int, current_user: str = Depends(get_current_user)):
    if db.get_property(property_id) is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db.calculate_monthly_revenue(property_id)
