from fastapi import FastAPI

app = FastAPI()


# Create
@app.post("/accounts")
async def post():
    # name, email, password, facebook access token
    account_id = 42
    return {"id": account_id}


# Read
@app.get("/accounts/{account_id}")
async def get(account_id):
    # authenticate with jwt
    return {"id": account_id}


@app.get("/accounts")
async def get():
    return {}


# Update
@app.put("/accounts/{account_id}")
async def put(account_id):
    # name, email, password, facebook access token
    return {"id": account_id}


# Delete
@app.delete("/accounts/{account_id}")
async def delete(account_id):
    return {"id": account_id}
