import { web3, data } from "./MyWeb3.js";

export async function sendEmailBonus(receiver, amount, res) {
    let tx = {
        to: receiver,
        value: web3.utils.toWei(amount.toString(), 'ether'),
        gasPrice: await web3.eth.getGasPrice(),
        nonce: await web3.eth.getTransactionCount(data.DEPLOYER_ADDRESS, 'pending')
    }
    try {
        tx.gas = await web3.eth.estimateGas(tx);
        const transaction = await web3.eth.accounts.signTransaction(tx, data.PRIVATE_KEY);
        const receipt = await web3.eth.sendSignedTransaction(transaction.rawTransaction)
            .once('transactionHash', hash => console.log('Transaction Hash:', hash));
            console.log('from ', receipt.from);
            console.log("to ", receipt.to);
            console.log("block nr ", receipt.blockNumber);
            console.log('eff.GasPrice ', receipt.effectiveGasPrice, ' End');
            return res.status(200).send({ hash: receipt.transactionHash, error: "no error" });

    } catch (err) {
        console.log('email tx sign or send failed:', err);
        return res.status(500).send({error:"email tx sign or send failed", errorObj:err});
    }
}