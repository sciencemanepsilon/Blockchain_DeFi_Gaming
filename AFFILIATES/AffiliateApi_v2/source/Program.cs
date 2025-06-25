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
    string BetId = ctx.Request.RouteValues["BetId"].ToString();
    double TxVol = Convert.ToDouble(ctx.Request.RouteValues["TxVol"]);
    string currency = ctx.Request.RouteValues["currency"].ToString();
    string TxHash = ctx.Request.Headers["tx-hash"].ToString();
    Better[] players = await ctx.Request.ReadFromJsonAsync<Better[]>();

    Console.WriteLine("START: SportBet, betId {0} nPl {1} TxHash {2}",
        BetId, players.Length, TxHash);
    if (TxHash == "") {
        Console.WriteLine("missing headers, End");
        return Results.Text("missing headers", statusCode: 400);
    }
    if (players.Length == 0) {
        Console.WriteLine("players array empty, End");
        return Results.Text("array is empty", statusCode: 400);
    }
    string pretty = "Sport Bet";
    double comm = MyEnv.SportBetComm;
    string dat = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
    foreach (Better pl in players) {
        await FireDB.RunTx(TxVol, comm, pl.Aid, pl.Uid, pl.Txid, dat, currency, pretty, TxHash);
    }
    Console.WriteLine("Outside loop, all done, End");
    return Results.Text("Success");
});



// Called by Frontend => Api-Proxy to fetch Affiliate Info 
app.MapGet("/AffiliateInfo/{uid}", async Task<IResult> (string uid) => {
    Console.WriteLine("START: AffiliateInfo uid {0}", uid);

    FireDB.AffiDoc doc = await FireDB.GetAffiliateInfo(uid);
    if (doc.TotalEarned == -9.2) return Results.Text(doc.JoinedAt, statusCode: 281);
    double share = Math.Round(((double)doc.TotalReferents*100)/MyEnv.N_users, 4);

    var Rn = await Referents.GetArray(uid, null, null);
    Console.WriteLine("AffiliateInfo, share {0}, End", share);
    return Results.Json(new AffiData(
        "no error", doc.TotalReferents, share, doc.TotalEarned,
        doc.Unclaimed, Rn.arr, doc.JoinedAt, doc.RevenuePercent, Rn.vm, Rn.lv1, Rn.lv2
    ));
});


// Called by Frontend => Api-Proxy to View Referents
app.MapGet("/GetReferents/{pagi1}/{pagi2}/{uid}",
    async Task<IResult> (string pagi1, string pagi2, string uid) => {

    Console.WriteLine("START: Get-Referents uid {0} lv1 {1} lv2 {2}", uid, pagi1, pagi2);
    string lv2 = pagi2 == "no"? null: pagi2;
    double? lv1 = pagi1 == "no"? null: Convert.ToDouble(pagi1);
    var Rn = await Referents.GetArray(uid, lv1, lv2);
    if (Rn.err != null) return Results.Text(Rn.err, statusCode: 283);
    Console.WriteLine("Get-Referents, End");
    return Results.Json(new ReferentsJsonResponse("no error", Rn.arr, Rn.vm, Rn.lv1, Rn.lv2));
});


app.MapGet("/ClaimTx/{uid}", async Task<IResult> (string uid) => {
    Console.WriteLine("START: ClaimTx uid {0}", uid);

    ClaimTx[] cHist = await ExeClaim.GetClaimTx(uid);
    Console.WriteLine("ClaimTx End");
    return Results.Json(cHist);
});


app.MapGet("/ReferentTx/{uid}/{pagi}", async Task<IResult> (string uid, string pagi) => {
    Console.WriteLine("START: ReferentTx uid {0} pagi {1}", uid, pagi);
    string lv = pagi == "no"? null: pagi;
    var Rn = await Referents.GetTxArray(uid, lv);
    if (Rn.err != null) return Results.Text(Rn.err, statusCode: 283);
    Console.WriteLine("ReferentTx End");
    return Results.Json(new {ViewMore=Rn.vm, TxArray=Rn.arr});
});


app.MapGet("/AffiliateRedeem/{vol}/{uid}/{wid}", async Task<IResult> (
    double vol, string uid, string wid) => {
    double UsdValue = 0.25;
    double usd = vol * UsdValue;
    Console.WriteLine(
        "START: ExeClaim uid {0} vol {1} pol/usd {2} usd {3} wid {4}",
        uid, vol, UsdValue, usd, wid
    );
    if (usd < MyEnv.MinClaim) return Results.Text("Claim too low", statusCode: 281);

    var eo = await ExeClaim.UpdateUnclaimed(uid, vol, UsdValue);
    if (eo.err == "tx failed") 
        return Results.Text("Network is busy. Try again", statusCode: 282);
    if (eo.err != "success") return Results.Text(eo.err, statusCode: 283);

    (string res, int code) = await Httpx.MakeRequest(
        MyEnv.LudoWeb3_URL + MyEnv.LudoWeb3_Route, HttpMethod.Post, null,
        new {emailAmount=vol, funcName="SendEmailBonus", emailReceiver=wid}
    );
    if (code != 200) {
        await ExeClaim.RollBackUnclaimed(uid, eo.un);
        return Results.Text("Money transfer failed. Try again", statusCode:284);
    }
    Httpx.Web3_Response ResWeb3 = Httpx.GetJsonResponse(res);
    await ExeClaim.WriteClaimTx(uid, "POL", ResWeb3.hash, vol);
    Console.WriteLine("END: ExeClaim TxHash {0}", ResWeb3.hash);
    return Results.Json(new { error="no error", hash=ResWeb3.hash });
});

app.Run();