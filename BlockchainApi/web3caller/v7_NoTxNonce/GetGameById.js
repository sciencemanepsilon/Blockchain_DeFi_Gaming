import { contract } from "./MyWeb3.js";
import { formatEther } from "ethers";

export async function exeGetGameById(req, res) {
    try {
        const gid = req.params.gameId;
        const game = await contract.getGameById(gid);
        const gameData = convertGameDataToJSON(game);
        console.log("min bet ", gameData.minBet, " status ", gameData.lastModified);
        return res.status(200).send({ msg: "success", game: gameData });
    } catch (error) {
        console.log("error in getGameId", error);
        return res.status(500).send({ msg: "fail" });
    }
}

const convertGameDataToJSON = (res) => ({
    admin: res.admin,
    media: res.media,
    gameId: res.gameId,
    gameType: res.gameType,
    autoHandStart: res.autoHandStart,
    isPublic: res.isPublic,
    players: res.players.map(player => ({
        playerId: player[0],
        wallet: Number(formatEther(player[1])),
        walletAddress: player[2],
        photoUrl: player[3],
        name: player[4]
    })),
    lastModified: Number(res.lastModified.toString()),
    rTimeout: Number(res.rTimeout.toString()),
    invPlayers: res.invPlayers || [],
    gameTime: res.gameTime? Number(res.gameTime.toString()):0,
    minBet: Number(formatEther(res.minBet))
});
