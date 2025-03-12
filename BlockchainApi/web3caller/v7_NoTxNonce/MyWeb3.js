import dotenv from "dotenv";
import { Contract, Wallet, JsonRpcProvider } from "ethers";

dotenv.config();
export let provider, contract, wallet, walletEmBonus;
export const GetGameByIdRoute = process.env.getGameByIdRoute;
export const getCommRateRoute = process.env.getCommRateRoute;
export const ContrFuncRoute = process.env.contractFuncRoute;
export const isPlaJoinedRoute = "/BlockChainApi/isPlayerJoined";

const data3 = [{
        abi: process.env.ABI,
        privKey: process.env.POKER_PRIVATE_KEY,
        conAddr: process.env.CONTRACT_ADDRESS},
    {
        abi: process.env.BLACKJACK_ABI,
        privKey: process.env.BLACKJACK_PRIVATE_KEY,
        conAddr: process.env.BLACKJACK_CONTRACT_ADDRESS},
    {
        abi: process.env.ABI_LUDO,
        privKey: process.env.LUDO_PRIVATE_KEY,
        conAddr: process.env.CONTRACT_ADDRESS_LUDO
}];
const ii = Number(process.env.GAME_SERVER_INDEX);

export let data = {
    abi: data3[ii].abi,
    CONTRACT_ADDRESS: data3[ii].conAddr,
    PRIVATE_KEY: data3[ii].privKey,
    PRIVATE_KEY_EMAIL_BONUS: process.env.EMAIL_BONUS_PRIVATE_KEY,
    PROVIDER_URL: JSON.parse(process.env.PROVIDER_URL),
    funcNames: process.env.SUPP_FUNC_NAMES.split("-")
};
console.log(`Contract: route ${ContrFuncRoute} addr ${data.CONTRACT_ADDRESS}`);
console.log(`ProvURL[0] ${data.PROVIDER_URL[0]} funcNames ${data.funcNames}`);

export function initializeWeb3(providerIndex) {
    const providerUrl = data.PROVIDER_URL[providerIndex];
    provider = new JsonRpcProvider(providerUrl);
    wallet = new Wallet(data.PRIVATE_KEY, provider);
    walletEmBonus = new Wallet(data.PRIVATE_KEY_EMAIL_BONUS, provider);
    contract =  new Contract(data.CONTRACT_ADDRESS, JSON.parse(data.abi), wallet);
    console.log(`Initialized web3 with provider URL: ${providerUrl}`);
}
initializeWeb3(0);