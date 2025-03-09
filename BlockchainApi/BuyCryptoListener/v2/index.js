import dotenv from "dotenv";
import Web3 from "web3";
import axios from "axios";

dotenv.config();
console.log("fetching env");
let isConn = false;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
const abi = process.env.ABI;
const providerArr = JSON.parse(process.env.WSS_PROVIDER_URL);
const PROVIDER_URL = providerArr[0];
const gamArr = JSON.parse(process.env.GameConfigArray);
const gameSer = gamArr[0].surl;
const pokerRoute = process.env.pokerServerBuyCoinsRoute;
console.log("enVars from configMap, contrAddr: ", CONTRACT_ADDRESS);
console.log(PROVIDER_URL);
console.log(gameSer);

function callGameServer(nam, bn, rv) {
    console.log(`eventName ${nam} blockNr ${bn} uid ${rv.playerId}`);
    console.log(`gameId ${rv.gameId} amount Big Int ${rv.amount}`);
    axios.post(
        gameSer + pokerRoute,
        {playerId:rv.playerId, gameId:rv.gameId, amount:rv.amount.toString()}
    ).then(res => console.log("poker res: ", res.status)
    ).catch(err => console.log(`pokerCallFailed, errName ${err.name} msg ${err.message}`));
    return 0;
}

async function connectToListner() {
    let provider = new Web3.providers.WebsocketProvider(PROVIDER_URL)
    provider.on('error', async error => {
        console.error('WebSocket Error:', error);
        return await reconnect();
    });
    provider.on('end', async error => {
        console.error('WebSocket Closed:', error);
        return await reconnect();
    });
    provider.on('connect', error => {
        console.error('WebSocket connect:', error);
    });
    provider.on('disconnect', async error => {
        console.error('WebSocket disconnect:', error);
        return await reconnect();
    });

    let web3 = new Web3(provider);
    let contract = new web3.eth.Contract(JSON.parse(abi), CONTRACT_ADDRESS);
    let sub = contract.events.BuyCoin(
        { fromBlock:0, toBlock: "latest" },
        (error, event) => {
            if (error) {console.log("event got error: ", error); }
            else { callGameServer(event.event, event.blockNumber, event.returnValues); }
    });

    if (sub) {
        sub.on("connected", sid => {
            isConn = true;
            console.log("listener connected, sid: ", sid);
        });
        sub.on("data", event => callGameServer(event.event, event.blockNumber, event.returnValues));
        sub.on('error', (error, receipt) => {
            console.log(`listener got error: ${error}`);
            if (receipt) { console.log("rejection receipt: ", receipt) }
            else { console.log("err with no receipt") }
        });
        sub.on('changed', event => console.log("change event: ", event));

        if (!isConn) {setTimeout(async () => {
            if (!isConn) {
                console.log("connect timeout, isConn: ",isConn," ,End");
                return await reconnect();
            }
            console.log("finally isConn: ", isConn);}, 10000);
        } else {console.log("isConn: ", isConn)}
    } else {
        console.log("subscription to listener is null: ", sub);
        return await reconnect();
    }
    console.log("outside of listen block, isConn is still: ", isConn);
}


async function reconnect() {
    console.log('Attempting to reconnect...');
    await new Promise(resolve => setTimeout(resolve, 5000)); 
    return await connectToListner();
}

let ReconnectId = await connectToListner();
console.log(`main scope: isConn=${isConn}, ReconnectId OR (void)=${ReconnectId}`);