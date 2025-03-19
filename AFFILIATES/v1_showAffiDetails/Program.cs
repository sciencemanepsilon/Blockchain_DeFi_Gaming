using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;
using Microsoft.AspNetCore.Routing;
using System;
using System.Threading.Tasks;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.UseRouting();
Console.WriteLine("Env: pfx {0} nUsers {1} qSize {2} RevFac {3}",
    MyEnv.pfx, MyEnv.N_users, MyEnv.ReferentQuerySize, MyEnv.RevenueFactor);


// Called by SportBetApi/DistributeFunds:
app.MapPost("/SportBetPayout/{BetId}/{TxVol}/{currency}", async Task<IResult> (HttpContext ctx) => {
    string from = "SportBet";
    string BetId = ctx.Request.RouteValues["BetId"].ToString();
    double TxVol = Convert.ToDouble(ctx.Request.RouteValues["TxVol"]);
    string currency = ctx.Request.RouteValues["currency"].ToString();
    string TxHash = ctx.Request.Headers["tx-hash"].ToString();
    Better[] players = await ctx.Request.ReadFromJsonAsync<Better[]>();

    Console.WriteLine("START: {0} betId {1} nPl {2} TxHash {3}",
        from, BetId, players.Length, TxHash);
    if (TxHash == "") {
        Console.WriteLine("missing headers, End");
        return Results.Text("missing headers", statusCode: 400);
    }
    if (players.Length == 0) {
        Console.WriteLine("players array empty, End");
        return Results.Text("array is empty", statusCode: 400);
    }
    (double comm, string pretty, string dat) = MyEnv.GetGameAtt(from);
    foreach (Better pl in players) {
        await FireDB.RunTx(TxVol, comm, pl.Aid, pl.Uid, pl.Txid, dat, currency, pretty, TxHash);
    }
    Console.WriteLine("Outside loop, all done, End");
    return Results.Text("Success");
});



// Called by LeaveTable-FinishHandApi:
app.MapPost("/GameTablePayout/{tid}/{currency}", async Task<IResult> (HttpContext ctx) => {
    string tid = ctx.Request.RouteValues["tid"].ToString();
    string currency = ctx.Request.RouteValues["currency"].ToString();
    string from = ctx.Request.Headers["from"].ToString();
    string TxHash = ctx.Request.Headers["tx-hash"].ToString();
    string FireTxId = ctx.Request.Headers["fire-txid"].ToString();
    Player[] players = await ctx.Request.ReadFromJsonAsync<Player[]>();

    Console.WriteLine("START: {0}/{1} nPl {2} TxHash {3} FireId",
        from, tid, players.Length, TxHash, FireTxId);

    (double comm, string pretty, string dat) = MyEnv.GetGameAtt(from);
    foreach (Player pl in players) {
        await FireDB.RunTx(pl.TxVol, comm, pl.Aid, pl.Uid, FireTxId, dat, currency, pretty, TxHash);
    }
    Console.WriteLine("Outside loop, all done, End");
    return Results.Text("Success");
});



// Called by Frontend => Api-Proxy to fetch Affiliate Info 
app.MapGet("/AffiliateInfo/{uid}", async Task<IResult> (string uid) => {
    Console.WriteLine("START: AffiliateInfo uid {0}", uid);

    (double total, int TotaRef,
        double unclm, string joined, int comm) = await FireDB.GetAffiliateInfo(uid);
    if (total == -9.2) {
        Console.WriteLine("{0}. End", joined);
        return Results.Text(joined, statusCode: 281);
    }
    Referent[] arr = await Referents.GetArray(uid, TotaRef);
    double share = Math.Round(((double)TotaRef*100)/MyEnv.N_users, 4);
    Console.WriteLine("AffiliateInfo, share {0}, End", share);
    return Results.Json(new AffiData(
        "no error", TotaRef, share, total, unclm, arr, joined, comm
    ));
});


// Called by Frontend => Api-Proxy to fetch claim tx
app.MapGet("/ClaimTx/{uid}", async Task<IResult> (string uid) => {
    Console.WriteLine("START: ClaimTx uid {0}", uid);

    ClaimTx[] cHist = await ExeClaim.GetClaimTx(uid);
    Console.WriteLine("ClaimTx End");
    return Results.Json(cHist);
});


// Called by Frontend => Api-Proxy to fetch referent tx
app.MapGet("/ReferentTx/{uid}", async Task<IResult> (string uid) => {
    Console.WriteLine("START: ReferentTx uid {0}", uid);

    ReferentTx[] arr = await Referents.GetTxArray(uid);
    Console.WriteLine("ReferentTx End");
    return Results.Json(arr);
});


// Called by Frontend => Api-Proxy to exe Claim
app.MapGet("/ExeClaim/{vol}/{UsdValue}/{uid}/{wid}", async Task<IResult> (
    double vol, double UsdValue, string uid, string wid) => {

    double usd = vol * UsdValue;
    Console.WriteLine(
        "START: ExeClaim uid {0} vol {1} pol/usd {2} usd {3} wid {4}",
        uid, vol, UsdValue, usd, wid
    );
    if (usd < MyEnv.MinClaim) return Results.Text("Claim too low", statusCode: 281);

    string err = await ExeClaim.UpdateUnclaimed(uid, vol, UsdValue);
    if (err == "tx failed") 
        return Results.Text("Network is busy. Try again", statusCode: 282);
    if (err != "success") return Results.Text(err, statusCode: 283);

    (string res, int code) = await Httpx.MakeRequest(
        "web3caller", HttpMethod.Get,
        null, new {vol=vol, uid=uid, wid=wid}
    );
    if (code != 200) return Results.Text("Send us email we will send money", statusCode:284);

    await ExeClaim.WriteClaimTx(uid, "POL", res, vol);
    Console.WriteLine("ExeClaim End");
    return Results.Text("Success");
});

app.Run();