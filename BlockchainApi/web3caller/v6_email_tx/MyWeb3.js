import dotenv from "dotenv";
import Web3 from "web3";

dotenv.config();
export let web3, contract, account;
export const gasTrackerApi = process.env.GAS_TRACKER_API;
export const gasTrackerApiKey = process.env.GAS_TRACKER_API_KEY;

export const GetGameByIdRoute = process.env.getGameByIdRoute;
export const getCommRateRoute = process.env.getCommRateRoute;
export const ContrFuncRoute = process.env.contractFuncRoute;
export const isPlaJoinedRoute = "/BlockChainApi/isPlayerJoined";

export let data = {
    abi: process.env.BLACKJACK_ABI, //ABI_LUDO, ABI
    PRIVATE_KEY: process.env.SMART_CON_PRIVATE_KEY,
    CONTRACT_ADDRESS: process.env.BLACKJACK_CONTRACT_ADDRESS, //CONTRACT_ADDRESS_LUDO, CONTRACT_ADDRESS
    PROVIDER_URL: JSON.parse(process.env.PROVIDER_URL),
    DEPLOYER_ADDRESS: process.env.DEPLOYER_ADDRESS,
    funcNames: process.env.SUPP_FUNC_NAMES.split("-"),
    GAS_PRICE: process.env.GAS_PRICE,
    GAS_LIMIT: Number(process.env.GAS_LIMIT)
};

console.log(`env gasPrice ${data.GAS_PRICE} gasLim ${data.GAS_LIMIT}`);
console.log(`Contract: route ${ContrFuncRoute} addr ${data.CONTRACT_ADDRESS}`);

export function initializeWeb3(providerIndex) {
    const providerUrl = data.PROVIDER_URL[providerIndex];
    web3 = new Web3(new Web3.providers.HttpProvider(providerUrl));
    contract = new web3.eth.Contract(JSON.parse(data.abi), data.CONTRACT_ADDRESS);
    account = web3.eth.accounts.privateKeyToAccount(data.PRIVATE_KEY);
    web3.eth.defaultAccount = account.address;
    console.log(`Initialized web3 with provider URL: ${providerUrl}`);
}
initializeWeb3(0);