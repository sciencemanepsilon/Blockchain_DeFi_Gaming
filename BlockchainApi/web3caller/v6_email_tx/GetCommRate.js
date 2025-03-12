import { web3, contract, data } from "./MyWeb3.js";

export async function exeGetCommRate(req, res) {
    try {
        let rate = await contract.methods.commissionRate().call({from:data.DEPLOYER_ADDRESS});
        var rateNum = web3.utils.toNumber(rate);
        console.log(`commRateRaw ${rate} toNumber ${rateNum}, End`);
        return res.status(200).send({ error: "no error", commissionRate: rateNum });
    } catch (e) {
        console.log("Failed to call getCommissionRate: ", e);
        return res.status(500).send({msg:"Failed to call getCommissionRate", error:e});
    }
}