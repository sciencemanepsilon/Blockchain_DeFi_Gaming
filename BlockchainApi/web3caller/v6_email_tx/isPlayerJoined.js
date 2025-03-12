import { contract, data } from "./MyWeb3.js";

export async function IsPlJoined(req, res) {
    try {
        const uid = req.params.userId;
        if (!uid) {
            return res.status(200).send({msg:"success", game: false});
        }
        const game = await contract.methods.isPlayerJoined(uid).call({from:data.DEPLOYER_ADDRESS});
        if(game){
            return res.status(200).send({msg:"success", gameId:game});
        }
        return res.status(200).send({msg:"success", game: false});
    }
    catch (error) {
        console.log("error in getGameId", error);
        return res.status(500).send({msg:"fail"});
    }
}