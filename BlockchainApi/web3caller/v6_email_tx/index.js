import express from "express";
import { exeGetGameById } from "./GetGameById.js";
import { IsPlJoined } from "./isPlayerJoined.js";
import { exeGetCommRate } from "./GetCommRate.js"
import { exeContrFunctions } from "./ContractFunctions.js";
import { GetGameByIdRoute, getCommRateRoute, ContrFuncRoute, isPlaJoinedRoute } from "./MyWeb3.js";

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.get("/BlockChainApi/hCheck", (r, s) => s.status(200).send("OK"));
app.get(getCommRateRoute,async (r, s) => await exeGetCommRate(r, s));
app.post(ContrFuncRoute, async (r, s) => await exeContrFunctions(r, s));
app.get(isPlaJoinedRoute +"/:userId", async (r, s) => await IsPlJoined(r, s));
app.get(GetGameByIdRoute +"/:gameId", async (r, s) => await exeGetGameById(r, s));

app.listen(8080, () => console.log('Listening on port 8080'));

process.on('unhandledRejection',
    (r, p) => console.log(`Unhandled Rejection: promise ${p} reason ${r}`)
);

process.on('uncaughtException', err => {
    console.error('Uncaught Exception thrown:', err);
    process.exit(0);
});