import express from "express";
import dotenv from "dotenv";
import Web3 from "web3";
import axios from "axios";
import {GoogleAuth} from "google-auth-library";

// init:
dotenv.config();
const app = express();
const port = process.env.PORT || 5000;
app.use(express.json());
app.use(express.urlencoded({extended: false}));
const SYS_CONFIG_API = process.env.SYS_CONFIG_API;

async function getJWT() {
    const auth = new GoogleAuth();
    const client = await auth.getIdTokenClient(SYS_CONFIG_API);
    return await client.idTokenProvider.fetchIdToken(SYS_CONFIG_API);
}

async function sysConfigCall(jwt) {
    return await axios.get(
        SYS_CONFIG_API, {
            params:{"oriApi":"BuyCoinsListener"},
            headers:{"Authorization":`Bearer ${jwt}`}}
    );
}

const jwt = await getJWT();
const res = await sysConfigCall(jwt);
let data = {
    CONTRACT_ADDRESS: res.data.contrAddr,
    PRIVATE_KEY: res.data.ownerWallet,
    abi: res.data.abi,
    PROVIDER_URL: res.data.provUrl
};
const gameSer = res.data.Server
console.log("init web3 done");


// Blockchain Listener Callback:
function callGameServer(nam, bn, rv) {
    console.log(`eventName ${nam} blockNr ${bn} uid ${rv.playerId}`);
    console.log(`gameId ${rv.gameId} amount Big Int ${rv.amount}`);
    axios.post(
        gameSer +"/buyCoins",
        {playerId:rv.playerId, gameId:rv.gameId, amount:rv.amount.toString()}
    ).then(res => console.log("response: ", res.status)).catch(
        err => console.log(`Request Failed, errName ${err.name} msg ${err.message}`)
    );
    return 0;
}

// Start listen to Polygon-Blockchain SmartContract.BuyCoin-Event:
let web3 = new Web3(new Web3.providers.WebsocketProvider(data.PROVIDER_URL));
let contract = new web3.eth.Contract(JSON.parse(data.abi), data.CONTRACT_ADDRESS);
let account = web3.eth.accounts.privateKeyToAccount(data.PRIVATE_KEY);
web3.eth.defaultAccount = account.address;

let sub = contract.events.BuyCoin(
    {fromBlock: 0, toBlock: "latest"},
    (error, event) => {
        if (error) {console.log("event got error: ", error);}
        else {callGameServer(event.event, event.blockNumber, event.returnValues);}
});
if (sub) {
    sub.on("connected", sid => console.log("listener connected, sid: ", sid));
    sub.on("data", event => callGameServer(event.event, event.blockNumber, event.returnValues));
} else {console.log("subscription to listener is null: ", sub);}


// Start Server to give feedback to Table Guard:
app.listen(port, () => console.log(`Listening on port ${port}`));

//called by TableGuard Manager that is called by create table downstream
app.get('/awake', async(req, res) => {
    console.log(`CreateTableDownStr => slowTabGuardManager: tid ${req.query.tid}, End`);
    res.status(200).send("wake up by create table done");
});

//called by Table Guard
app.get("/keepAlive", async(req,res) => {
    console.log(`keepAlive by TabGuard ${req.query.tid}, End`);
    res.status(200).send("keep alive success");
});