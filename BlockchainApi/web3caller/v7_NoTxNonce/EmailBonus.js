import { provider, walletEmBonus } from "./MyWeb3.js";
import { parseUnits } from "ethers";

export async function sendEmailBonus(receiver, amount, res) {
    const feeData = await provider.getFeeData();
    let trans = {
        to: receiver,
        value: parseUnits(amount.toString(), 'ether'),
        maxFeePerGas: feeData.maxFeePerGas,
        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
    }
    try {
        const tx = await walletEmBonus.sendTransaction(trans);
        const receipt = await tx.wait();
        console.log("Transaction sent! Hash:", tx.hash);
        console.log('from ', receipt.from);
        console.log("to ", receipt.to);
        console.log("block nr ", receipt.blockNumber, ' End');
        return res.status(200).send({ hash: tx.hash, error: "no error" });

    } catch (err) {
        console.log('email tx sign or send failed:', err);
        return res.status(500).send({error:"email tx sign or send failed", errorObj:err});
    }
}