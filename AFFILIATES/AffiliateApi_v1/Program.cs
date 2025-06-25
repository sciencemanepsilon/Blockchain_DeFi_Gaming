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



// Called by Frontend => Api-Proxy to fetch Affiliate Info 
app.MapGet("/AffiliateInfo/{uid}", async Task<IResult> (string uid) => {
    string od = "DESC";
    string of = "earned";
    Console.WriteLine("START: AffiliateInfo uid {0}", uid);

    FireDB.AffiDoc doc = await FireDB.GetAffiliateInfo(uid);
    if (doc.TotalEarned == -9.2) return Results.Text(doc.JoinedAt, statusCode: 281);
    double share = Math.Round(((double)doc.TotalReferents*100)/MyEnv.N_users, 4);

    var Rn = await Referents.GetArray<double?>(uid, of, od, null);
    Console.WriteLine("AffiliateInfo, share {0}, End", share);
    return Results.Json(new AffiData<double?>(
        "no error", doc.TotalReferents, share, doc.TotalEarned,
        doc.Unclaimed, Rn.arr, doc.JoinedAt, doc.RevenuePercent, Rn.vm, Rn.lv
    ));
});


// Called by Frontend => Api-Proxy to View Referents
app.MapGet("/GetReferents/{of}/{od}/{pagi}/{uid}",
    async Task<IResult> (string of, string od, string pagi, string uid) => {
    if (Referents.ofs.Contains(of) == false) {
        Console.WriteLine("invalid OrderBy-Field: {0}, End", of);
        return Results.Text("invalid OrderBy-Field", statusCode: 282);
    }
    Console.WriteLine("START: Get-Referents uid {0} of {1} od {2} pagi {3}", uid, of, od, pagi);
    if (of == "earned") {
        double? PagiNum = pagi == "no"? null: Convert.ToDouble(pagi);
        var Rn = await Referents.GetArray<double?>(uid, of, od, PagiNum);
        if (Rn.err != null) return Results.Text(Rn.err, statusCode: 283);
        Console.WriteLine("Get-Referents, End");
        return Results.Json(new ReferentsJsonResponse<double?>("no error", Rn.arr, Rn.vm, Rn.lv));
    }
    string PagiStr = pagi == "no"? null: pagi;
    var Rs = await Referents.GetArray<string>(uid, of, od, PagiStr);
    if (Rs.err != null) return Results.Text(Rs.err, statusCode: 283);
    Console.WriteLine("Get-Referents, End");
    return Results.Json(new ReferentsJsonResponse<string>("no error", Rs.arr, Rs.vm, Rs.lv));
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
app.MapGet("/AffiliateRedeem/{vol}/{UsdValue}/{uid}/{wid}", async Task<IResult> (
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
        MyEnv.LudoWeb3_URL + MyEnv.LudoWeb3_Route, HttpMethod.Post, null,
        new {emailAmount=vol, funcName="SendEmailBonus", emailReceiver=wid}
    );
    if (code != 200) return Results.Text("Send us email we will send money", statusCode:284);

    Httpx.Web3_Response ResWeb3 = Httpx.GetJsonResponse(res);
    await ExeClaim.WriteClaimTx(uid, "POL", ResWeb3.hash, vol);
    Console.WriteLine("END: ExeClaim TxHash {0}", ResWeb3.hash);
    return Results.Json(new { error="no error", hash=ResWeb3.hash });
});

app.Run();