import dotenv from "dotenv";
import Web3 from "web3";
import axios from "axios";

dotenv.config();
console.log("fetching env");
let isConn = false;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
const PRIVATE_KEY = process.env.SMART_CON_PRIVATE_KEY;
const abi = process.env.ABI;
const providerArr = JSON.parse(process.env.WSS_PROVIDER_URL);
const PROVIDER_URL = providerArr[0];
const gamArr = JSON.parse(process.env.GameConfigArray);
const gameSer = gamArr[0].surl;
const pokerRoute = process.env.pokerServerBuyCoinsRoute;
console.log("enVars from configMap, contrAddr: ", CONTRACT_ADDRESS);
console.log(PRIVATE_KEY);
console.log(PROVIDER_URL);
console.log(gameSer);

function callGameServer(nam, bn, rv) {
    console.log(`eventName ${nam} blockNr ${bn} uid ${rv.playerId}`);
    console.log(`gameId ${rv.gameId} amount Big Int ${rv.amount}`);
    axios.post(
        gameSer + pokerRoute,
        {playerId:rv.playerId, gameId:rv.gameId, amount:rv.amount.toString()}
    ).then(res => console.log("res: ", res.status)).catch(
        err => console.log(`Request Failed, errName ${err.name} msg ${err.message}`)
    );
    return 0;
}
let web3 = new Web3(new Web3.providers.WebsocketProvider(PROVIDER_URL));
let contract = new web3.eth.Contract(JSON.parse(abi), CONTRACT_ADDRESS);
let account = web3.eth.accounts.privateKeyToAccount(PRIVATE_KEY);
web3.eth.defaultAccount = account.address;
console.log("web3 init done, account.addr: ", account.address);

let sub = contract.events.BuyCoin(
    {fromBlock: 0, toBlock: "latest"},
    (error, event) => {
        if (error) {console.log("event got error: ", error);}
        else {callGameServer(event.event, event.blockNumber, event.returnValues);}
});

if (sub) {
    sub.on("connected", sid => {
        isConn = true;
        console.log("listener connected, sid: ", sid);
    });
    sub.on("data", event => callGameServer(event.event, event.blockNumber, event.returnValues));
    sub.on('error', (error, receipt) => {
        console.log(`listener got error: ${error}`);
        if (receipt) {console.log("rejection receipt: ", receipt)}
        else {console.log("err with no receipt")}
    });
    sub.on('changed', event => console.log("change event: ", event));

    if (!isConn) {
        setTimeout(() => {
            if (!isConn) {
                console.log("connect timeout, isConn: ",isConn," ,Exit");
                process.exit(0);
            }
            console.log("finally isConn: ", isConn);
        }, 20000);
    } else {console.log("isConn: ", isConn)}
} else {
    console.log("subscription to listener is null: ", sub);
    process.exit(0);
}
console.log("outside of listen block, isConn is still: ", isConn);

function exeSIGTERM(signal) {
    console.log("got SIGTERM: ", signal);
    if (sub) {
        try {
            sub.removeAllListeners();
            console.log("removeAllListeners worked");
        } catch {
            try {
                sub.unsubscribe();
                console.log("rmAllListeners failed, but sub.unsubscribe worked");
            } catch {console.log("both did not work");}
        }
    } else {console.log("web3 listener not found, exit conainer");}
    process.exit(0);
}

process.on('SIGTERM', exeSIGTERM);