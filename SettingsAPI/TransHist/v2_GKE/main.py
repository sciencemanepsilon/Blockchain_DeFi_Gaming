import uvicorn
from os import environ
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from transHist import max_pagin, iterateList

app = FastAPI()
route = "/TransHist/prod"
pfx = environ['DB_COLL_PREFIX']
myOris = environ['ALLOWED_ORIGINS'].split("||")
corsKwargs = {
    "allow_origins":myOris[0],
    "allow_methods":["GET", "OPTIONS"], "allow_headers":["lb-encrypted"]
}
if not pfx:
    route = "/TransHist/beta"
    corsKwargs['allow_origins'] = myOris
    corsKwargs['allow_origin_regex'] = myOris[-1]

app.add_middleware(CORSMiddleware, **corsKwargs)
print(f"got env: route {route} pfx {pfx} oris {myOris}")

@app.get('/TransHist/HealthCheck')
async def thisHealthCheck():
    return "Health-Check-Success"

@app.get(route)
async def makeTransHist(usid:str, paginate:int, page:int):
    # WEITER: add cashing + firestore query pagination snapshot
    if usid in ["", "undefined", "null", "Object Object"]:
        print("invalid uid ", usid, ", End")
        return {'error':'invalid user id'}
    if paginate < 1 or paginate > max_pagin or page < 1:
        print("invalid pagination or page value, End")
        return {'error':'invalid pagination or page value'}
    print(f"got params {usid} pagin {paginate} page {page}")

    msg, L, arrF = iterateList(usid, page, paginate)
    if msg:
        print(msg, ", End")
        return {"error":"bad pagination values"}
    return {"error":"no error", "transactions":arrF, "queryCount":L}


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT', 8080)))