import facebook
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel


# Reference: https://developers.facebook.com/docs/graph-api/reference/user/#default-public-profile-fields
FB_PUBLIC_PROFILE_FIELDS = "id,first_name,last_name,middle_name,name,name_format,picture,short_name"
PUBLIC_PROFILE_ENDPOINT = "/me?fields=" + FB_PUBLIC_PROFILE_FIELDS
PUBLIC_PROFILE_FIELD = "public_profile"
AUTH_JWT_SECRET_KEY = "secret"


class Account(BaseModel):
    name: str
    email: str
    password: str
    fb_access_token: str


class LoginData(BaseModel):
    email: str
    password: str


class Settings(BaseModel):
    authjwt_secret_key: str = AUTH_JWT_SECRET_KEY


app = FastAPI()


db = []


@AuthJWT.load_config
def get_config():
    return Settings()


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def check_fb_permission(graph, permission):
    permissions = graph.get_permissions(user_id='me')
    if permission not in permissions:
        raise HTTPException(status_code=400, detail=f'permission "{permission}" not granted')


def get_fb_profile(fb_access_token):
    graph = facebook.GraphAPI(access_token=fb_access_token)
    check_fb_permission(graph, PUBLIC_PROFILE_FIELD)
    return graph.request(PUBLIC_PROFILE_ENDPOINT)


# Create ---------------------------
@app.post("/accounts")
async def create(account: Account):
    # TODO: insert in a real db
    db.append(account)
    return account


# Login ----------------------------
@app.post('/login')
def login(login: LoginData, Authorize: AuthJWT = Depends()):
    # TODO: check email and password against db
    if login.email != 'raios.catodicos@gmail.com' or login.password != "test":
        raise HTTPException(status_code=400, detail="Bad email or password")

    access_token = Authorize.create_access_token(subject=login.email)
    return {"access_token": access_token}


# Read ------------------------------
@app.get("/accounts/me")
async def read(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()

    # TODO: get account by id from a real db
    account = db[0]

    profile = get_fb_profile(account.fb_access_token)

    return {
        "account": current_user,
        "fb_public_profile": profile
    }


@app.get("/accounts")
async def read():
    # TODO: get accounts from a real db
    return db


# Update ------------------------------
@app.put("/accounts/me")
async def update(account: Account, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()

    # TODO: find user and update with new data
    return current_user


# Delete ------------------------------
@app.delete("/accounts/me")
async def delete(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()

    # TODO: find user and delete account
    return current_user

