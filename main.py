from bson import ObjectId
import facebook
import motor.motor_asyncio
from fastapi import FastAPI, Body, HTTPException, Request, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel, Field, EmailStr


# Settings --------------------------------------
# Reference: https://developers.facebook.com/docs/graph-api/reference/user/#default-public-profile-fields
FB_PUBLIC_PROFILE_FIELDS = "id,first_name,last_name,middle_name,name,name_format,picture,short_name"
PUBLIC_PROFILE_ENDPOINT = "/me?fields=" + FB_PUBLIC_PROFILE_FIELDS
PUBLIC_PROFILE_FIELD = "public_profile"
AUTH_JWT_SECRET_KEY = "secret"
MONGODB_USER = 'user'
MONGODB_PASSWORD = 'password'
MONGODB_CONNECTION = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASSWORD}@cluster0.opzag.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"


# Starting App + DB ------------------------------
app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_CONNECTION)
db = client.db


# Model ------------------------------------------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class AccountModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    fb_access_token: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UpdateAccountModel(BaseModel):
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    fb_access_token: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class LoginData(BaseModel):
    email: str
    password: str


class Settings(BaseModel):
    authjwt_secret_key: str = AUTH_JWT_SECRET_KEY


@AuthJWT.load_config
def get_config():
    return Settings()


# helpers ---------------------------------------
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.message})


def check_fb_permission(graph, permission):
    permissions = graph.get_permissions(user_id='me')
    if permission not in permissions:
        raise HTTPException(status_code=400,
                            detail=f'permission "{permission}" not granted')


def get_fb_profile(fb_access_token):
    graph = facebook.GraphAPI(access_token=fb_access_token)
    check_fb_permission(graph, PUBLIC_PROFILE_FIELD)
    return graph.request(PUBLIC_PROFILE_ENDPOINT)


# Create ---------------------------
@app.post("/accounts")
async def create(account: AccountModel = Body(...)):
    account = jsonable_encoder(account)
    new_account = await db['accounts'].insert_one(account)
    created_account = await db['accounts'].find_one({"_id": new_account.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_account)


# Login ----------------------------
@app.post('/login')
async def login(login: LoginData, Authorize: AuthJWT = Depends()):
    account = await db['accounts'].find_one({"email": login.email, "password": login.password})
    if account is None:
        raise HTTPException(status_code=404, detail="Bad email or password")
    access_token = Authorize.create_access_token(subject=login.email)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"access_token": access_token})


# Read ------------------------------
@app.get("/accounts")
async def read():
    """ Returns a list of accounts.
    """
    accounts = await db['accounts'].find().to_list(100)
    return JSONResponse(status_code=status.HTTP_200_OK, content=accounts)


@app.get("/accounts/me")
async def read(Authorize: AuthJWT = Depends()):
    """ Returns the logged in account + data gathered from its fb profile
    """
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()

    account = await db["accounts"].find_one({"email": email})
    if account is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile = get_fb_profile(account["fb_access_token"])
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"account": account,
                                 "fb_public_profile": profile})


# Update ------------------------------
@app.put("/accounts/me")
async def update(account: UpdateAccountModel = Body(...), Authorize: AuthJWT = Depends()):
    """ Updates the logged in account with given fields
    """
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    account = {k:v for k, v in account.dict().items() if v is not None}

    if len(account) >= 1:
        transaction = await db["accounts"].update_one({"email": email},
                                                      {"$set": account})
        if transaction.modified_count == 1:
            updated_account = await db["accounts"].find_one({"email": email})
            if updated_account is not None:
                return JSONResponse(status_code=status.HTTP_200_OK,
                                    content=updated_account)

    existing_account = await db["accounts"].find_one({"email": email})
    if existing_account is not None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=existing_account)

    raise HTTPException(status_code=404, detail=f"Account {email} not found")


# Delete ----------------------------
@app.delete("/accounts/me")
async def delete(Authorize: AuthJWT = Depends()):
    """ Deletes the logged in account
    """
    Authorize.jwt_required()
    email = Authorize.get_jwt_subject()
    transaction = await db["accounts"].delete_one({"email": email})

    if transaction.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail="Account not found")
