import dotenv from "dotenv";
import Web3 from "web3";
import axios from "axios";

dotenv.config();
let provider, web3, contract, sub;
const ii = Number(process.env.GAME_SERVER_INDEX);
const gamArr = JSON.parse(process.env.GameConfigArray);
const providerArr = JSON.parse(process.env.WSS_PROVIDER_URL);
const data3 = [{
        abi: process.env.ABI,
        conAddr: process.env.CONTRACT_ADDRESS,
        coinsRoute: process.env.pokerServerBuyCoinsRoute},
    {
        abi: process.env.BLACKJACK_ABI,
        conAddr: process.env.BLACKJACK_CONTRACT_ADDRESS,
        coinsRoute: process.env.BlackJackServerBuyCoinsRoute},
    {
        abi: process.env.ABI_LUDO,
        conAddr: process.env.CONTRACT_ADDRESS_LUDO,
        coinsRoute: process.env.LudoServerBuyCoinsRoute
}]
const abi = data3[ii].abi;
const BuyCoinsRoute = data3[ii].coinsRoute;
const CONTRACT_ADDRESS = data3[ii].conAddr;
const PROVIDER_URL = providerArr[0];
const gameSer = gamArr[ii].surl;
const MAX_RECONNECTS = Number(process.env.MAX_BUYIN_LISTEN_RECONNECTS);
const RECONNECT_DELAY = Number(process.env.BUYIN_LISTEN_RECONNECT_DELAY_MILLI_SECONDS);
console.log(`env conAddr ${CONTRACT_ADDRESS} provURL ${PROVIDER_URL} gameSrv ${gameSer}`);


function callGameServer(nam, bn, rv) {
    console.log(`eventName ${nam} blockNr ${bn} uid ${rv.playerId}`);
    console.log(`gameId ${rv.gameId} amount Big Int ${rv.amount}`);
    axios.post(
        gameSer + BuyCoinsRoute,
        {playerId:rv.playerId, gameId:rv.gameId, amount:rv.amount.toString()}
    ).then(res => console.log("res: ", res.status)
    ).catch(err => console.log(`CallFailed, errName ${err.name} msg ${err.message}`));
    return 0;
}


async function handleWsErr(myMsg, event, nWsErr, nWsCon, remProvider) {
    var msg = "web3 sub is null, set new one";
    console.log(`${myMsg}: ${event}, nWsCon ${nWsCon} nWsErr ${nWsErr} remProv ${remProvider}`);

    if (remProvider) {provider.disconnect(1000, 'Reconnecting')}
    if (nWsErr >= MAX_RECONNECTS) {
        exeSIGTERM("max ws Err reached, exiting container.");
    }
    if (sub) {
        sub.removeAllListeners();
        msg = "removeAllListeners worked";
    }
    console.log(msg);
    await new Promise(resolve => setTimeout(resolve, RECONNECT_DELAY));
    return await connectToListner(nWsCon, nWsErr);
}


async function connectToListner(nWsCon, nWsErr) {
    provider = new Web3.providers.WebsocketProvider(PROVIDER_URL);
    provider.on('error', async error => await handleWsErr("WebSocket Error", error, nWsErr + 1, nWsCon, true));
    provider.on('end', async enddMsg => await handleWsErr("WebSocket Closed", enddMsg, nWsErr + 1, nWsCon, false));
    provider.on('disconnect', async dis => await handleWsErr("WebSocket disconnect", dis, nWsErr + 1, nWsCon, false));

    provider.on('connect', async conn => {
        console.log(`WebSocket connect: ${conn} nWsCon ${nWsCon} nWsErr ${nWsErr}`);
        if (nWsCon >= MAX_RECONNECTS) {
            provider.disconnect(1000, 'Reconnecting');
            exeSIGTERM("max ws connect reached, exiting container.");
        }
        if (web3) {web3.setProvider(provider)}
        else {web3 = new Web3(provider)}
        
        nWsCon = nWsCon + 1;
        contract = new web3.eth.Contract(JSON.parse(abi), CONTRACT_ADDRESS);

        sub = contract.events.BuyCoin({fromBlock:0, toBlock:"latest"}, (error, event) => {
            if (error) {console.log("event got error: ", error)}
            else {callGameServer(event.event, event.blockNumber, event.returnValues)}
        });
        if (sub) {
            sub.on("connected", sid => console.log("listener connected, sid: ", sid));
            sub.on("data", event => callGameServer(event.event, event.blockNumber, event.returnValues));
            sub.on('error', (error, receipt) => console.log(`sub error: ${error} receipt ${receipt}`));
            sub.on('changed', event => console.log("change event: ", event));
        } else {
            return await handleWsErr("sub is null", sub, nWsErr, nWsCon, true);
        }
    });
    console.log("connectToListener() finished")
    return [nWsCon, nWsErr];
}


function exeSIGTERM(signal) {
    console.log("got SIGTERM: ", signal);
    if (sub) {
        sub.removeAllListeners();
        console.log("removeAllListeners worked");
    } else {console.log("web3 listener not found, exit conainer")}
    process.exit(0);
}

process.on('SIGTERM', exeSIGTERM);
let rval = await connectToListner(0,0);
console.log("back in main scope, connToListender() returned ", rval);