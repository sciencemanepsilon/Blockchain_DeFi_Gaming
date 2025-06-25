import uvicorn
from fastapi import FastAPI
from statsLib import initTx
# called by sports-bet-api, no pubsub

app = FastAPI()

@app.get('/SportTxStats/{uid}')
async def UpdateSportStats(
    uid:str, action:str, amount:float, bid:str, fee:float, txHash:str, txId:str = None):

    res = initTx(uid, action, amount, bid, fee, txHash, txId)
    print("tx: ", res)
    return res

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)