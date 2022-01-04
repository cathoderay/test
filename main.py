import facebook
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Reference: https://developers.facebook.com/docs/graph-api/reference/user/#default-public-profile-fields
FB_PUBLIC_PROFILE_FIELDS = "id,first_name,last_name,middle_name,name,name_format,picture,short_name"
PUBLIC_PROFILE_ENDPOINT = "/me?fields=" + FB_PUBLIC_PROFILE_FIELDS
PUBLIC_PROFILE_FIELD = "public_profile"


class Account(BaseModel):
    name: str
    email: str
    password: str
    fb_access_token: str


app = FastAPI()

db = []


def check_permission(graph, permission):
    permissions = graph.get_permissions(user_id='me')
    if not permission in permissions:
        raise HTTPException(status_code=400,
                            detail=f'permission {permission} is not granted')


def get_fb_profile(fb_access_token):
    graph = facebook.GraphAPI(access_token=fb_access_token)
    check_permission(graph, PUBLIC_PROFILE_FIELD)
    return graph.request(PUBLIC_PROFILE_ENDPOINT)


# Create
@app.post("/accounts")
async def post(account: Account):
    # TODO: insert in a real db
    db.append(account)
    return account


# Read
@app.get("/accounts/{account_id}")
async def get(account_id: int):
    # TODO: authenticate with jwt

    # TODO: get account by id from a real db
    account = db[0]

    profile = get_fb_profile(account.fb_access_token)

    return {
        "account": account_id,
        "fb_public_profile": profile
    }


@app.get("/accounts")
async def get():
    # TODO: get accounts from a real db
    return db


# Update
@app.put("/accounts/{account_id}")
async def put(account_id: int):
    # TODO: update account
    return {"account": account_id}


# Delete
@app.delete("/accounts/{account_id}")
async def delete(account_id: int):
    # TODO: delete account
    return {"account": account_id}
