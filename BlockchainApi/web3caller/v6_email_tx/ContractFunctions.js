import axios from "axios";
import { sendEmailBonus } from "./EmailBonus.js";
import { 
    contract, data, web3, initializeWeb3,
    gasTrackerApi, gasTrackerApiKey } from "./MyWeb3.js";

let providerIndex = 0;
let FGP = data.GAS_PRICE;
let gasTrackerCash = {value: null, age: null};

async function handleTransaction(funcName, args, FGP, res) {
    let txHash = "";
    console.log("args", args);
    try {
        const transactionData = contract.methods[funcName](...args).encodeABI(); 
        const gasEstimate = await contract.methods[funcName](...args).estimateGas({from: data.DEPLOYER_ADDRESS});
        const intGasEstimate = Math.floor(Number(gasEstimate) * 1.2);
        console.log("gas", intGasEstimate);

        const nonce = await web3.eth.getTransactionCount(data.DEPLOYER_ADDRESS, 'pending');
        const baseFee = await web3.eth.getGasPrice();
        const maxPriorityFeePerGas = FGP;
        const maxFeePerGas = BigInt(baseFee) + BigInt(maxPriorityFeePerGas); // Total fee
        console.log(
            "baseFee", baseFee,
            "maxFeePerGas", maxFeePerGas.toString(),
            "maxPriorityFeePerGas", maxPriorityFeePerGas
        );
        const signedTrans = await web3.eth.accounts.signTransaction({
            to: data.CONTRACT_ADDRESS,
            nonce, data: transactionData,
            from: data.DEPLOYER_ADDRESS,
            gas: BigInt(intGasEstimate),
            maxFeePerGas: maxFeePerGas.toString(),
            maxPriorityFeePerGas: maxPriorityFeePerGas,
        }, data.PRIVATE_KEY);
        try {
            const receipt = await web3.eth.sendSignedTransaction(signedTrans.rawTransaction)
            .once('transactionHash', hash => {console.log('Transaction Hash:', hash); txHash = hash;});
            console.log(`from ${receipt.from} to ${receipt.to} Block ${receipt.blockNumber}`);
            console.log('eff.GasPrice ', receipt.effectiveGasPrice, ' End');
            return res.status(200).send({ hash: receipt.transactionHash, error: "no error" });
        } catch (error) {
            console.log("error", error);
            if (error.message.includes("TransactionBlockTimeoutError")) {
                console.log("tx timeout Error: ", error);
                const newFGP = Number(FGP) * 1.6
                console.log("recalling tx with double Gas Price: ", newFGP);
                return await handleTransaction(funcName, args, newFGP.toString(), res);
            }
        }
    } catch (error) {
        console.log('Transaction Error:', error.message, ', fullErr: ', error);
        if (error.message.includes("unavailable")) {
            //check game exist
            const game = await contract.methods.getGameById(args[0]).call({ from: data.DEPLOYER_ADDRESS });
            if (!game.gameId) {
                return res.status(200).send({ hash: txHash, error: "no error" });
            } else {
                providerIndex = (providerIndex + 1) % data.PROVIDER_URL.length;
                console.log(`Switching to provider URL at index ${providerIndex}`);
                initializeWeb3(providerIndex);
                return await handleTransaction(funcName, args, FGP, res);
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
    if (gasTrackerCash.value && Date.now() - gasTrackerCash.age < 30000) {
        FGP = gasTrackerCash.value;
        if (!Number(FGP) || FGP === 0) {FGP = data.GAS_PRICE;}
        console.log("cached GasPrice used: ", FGP);
    }
    else {
        const erg = await axios.get(gasTrackerApi + gasTrackerApiKey);
        if (erg.status != 200) {
            console.log(`GasApiRes: ${erg.status} ${erg.statusText}`);
            FGP = data.GAS_PRICE;
        }
        else {
            if (!Number(erg.data.result.FastGasPrice)) {
                FGP = data.GAS_PRICE;
                console.log("GasTracker failed, new FGP: ", FGP);
            } else {
                FGP = web3.utils.toWei((Number(erg.data.result.FastGasPrice)).toString(), 'gwei');
                if (FGP === 0) {FGP = data.GAS_PRICE;}
                else {
                    gasTrackerCash.value = FGP;
                    gasTrackerCash.age = Date.now();
                }
                console.log("GasTracker called, new FGP: ", FGP);
            }
        }
    }
    return await handleTransaction(funcName, args, FGP, res);
    } catch (err) {
        console.log(err)
    }
}