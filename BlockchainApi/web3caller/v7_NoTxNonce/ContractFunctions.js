import axios from "axios";
import { parseUnits } from "ethers";
import { sendEmailBonus } from "./EmailBonus.js";
import { contract, data, initializeWeb3, provider } from "./MyWeb3.js";

let providerIndex = 0;


async function getCurrentGasPrice() {
    try {
        const res = await axios.get("https://api.blocknative.com/gasprices/blockprices?chainid=137");
        if (res.data && res.data.blockPrices[0]) {
            const maxFeePerGas = parseUnits(res.data.blockPrices[0].estimatedPrices[0].maxFeePerGas.toString(), "gwei");
            const maxPriorityFeePerGas = parseUnits(res.data.blockPrices[0].estimatedPrices[0].maxPriorityFeePerGas.toString(), "gwei");
            console.log("gas from BlockNative");
            return { maxFeePerGas, maxPriorityFeePerGas }
        }
        const feeData = await provider.getFeeData()
        console.log("gas from FeeData");
        return {...feeData}
    } catch (error) {
        console.log("error: ", error);
        const feeData = await provider.getFeeData()
        return {...feeData}
    }
}

async function EstimateGas(funcName, args, res) {
    try {
        let gasEstimate = await contract[funcName].estimateGas(...args);
        gasEstimate = Math.floor(Number(gasEstimate) * 1.5);
        console.log("contract.estimateGas: ", gasEstimate);
        return gasEstimate;
    } catch (error) {
        console.log('contract.estimateGas Error:', error.message);
        console.log("End");
        return res.status(281).send({ error: "transaction failed", errObject: error });
}}



async function handleTransaction(funcName, args, res) {
    let txHash = "";
    console.log("args", args);
    const gasEstimate = await EstimateGas(funcName, args, res);
    const { maxFeePerGas,  maxPriorityFeePerGas} = await getCurrentGasPrice();
    console.log("fees: ", {maxFeePerGas, maxPriorityFeePerGas});
    try {
        const tx = await contract[funcName](...args, {
            maxFeePerGas: maxFeePerGas *BigInt(2),
            maxPriorityFeePerGas: maxPriorityFeePerGas,
            gasLimit: BigInt(gasEstimate)
            //gasLimit: BigInt(Number("1000000"))
        });
        console.time("transactionConfirm");
        const receipt = await tx.wait();
        console.timeEnd("transactionConfirm")
        txHash = receipt.hash;
        console.log('Transaction Hash:', txHash);
        console.log(`from ${receipt.from} to ${receipt.to} Block ${receipt.blockNumber}, End`);
        return res.status(200).send({ hash: txHash, error: "no error" });
    } catch (error) {
        console.log('Transaction Error:', error.message, ', fullErr: ', error);
        if (error.message.includes("unavailable")) {
            //check game exist
            const game = await contract.getGameById(args[0]);
            if (!game.gameId) {
                return res.status(200).send({ hash: txHash, error: "no error" });
            } else {
                providerIndex = (providerIndex + 1) % data.PROVIDER_URL.length;
                console.log(`Switching to provider URL at index ${providerIndex}`);
                initializeWeb3(providerIndex);
                return await handleTransaction(funcName, args, res);
            }
        } else {
            console.log("avaiblable, some other error");
            return res.status(281).send({ error: "transaction failed", errObject: error });
        }
    }
}

export async function exeContrFunctions(req, res) {
    const tid = req.body.tid;
    const funcName = req.body.funcName;
    let args, emailReceiver, emailAmount;
    console.log("function ", funcName);
    try {
    if (!data.funcNames.includes(funcName)) {
        console.log("invalid funcName: ", funcName, ", End");
        return res.status(500).send("invalid function name");
    }
    if (funcName === "changeCommissionRate") {args = [req.body.commissionRate];}
    if (funcName === "SendEmailBonus") {
        emailReceiver = req.body.emailReceiver;
        emailAmount = req.body.emailAmount;
        console.log(`emailReceiver ${emailReceiver} emailAccount ${emailAmount}`)

        if (!emailAmount || !emailReceiver) {
            console.log("missing email params, End");
            return res.status(500).send({error:"missing email params"});
        }
        return await sendEmailBonus(emailReceiver, emailAmount, res);
    }
    if (funcName === "leaveGame" || funcName === "finishHand") {
        args = [tid, req.body.playersArr, Date.now()];
    }
    return await handleTransaction(funcName, args, res);
    } catch (err) {console.log(err)}
}