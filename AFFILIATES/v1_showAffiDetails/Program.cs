using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;
using Microsoft.AspNetCore.Routing;
using System;
using System.Threading.Tasks;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.UseRouting();
Console.WriteLine("Env: pfx {0} nUsers {1} qSize {2} RevPercent {3}",
    MyEnv.pfx, MyEnv.N_users, MyEnv.ReferentQuerySize, MyEnv.RevenuePercent);


// Called by Connect Wallet on create account success
app.MapGet("/CreateAffiliateRecord/{uid}", async Task<IResult> (HttpContext ctx) => {
    string uid = ctx.Request.RouteValues["uid"].ToString();
    Console.WriteLine("START: AffiliateRecord uid {0}", uid);

    await FireDB.CreateAffiliateRecord(uid);
    Console.WriteLine("AffiliateRecord created, End");
    return Results.Text("Success");
});

// Called by Frontend => Api-Proxy to fetch Affiliate Info 
app.MapGet("/AffiliateInfo/{uid}", async Task<IResult> (HttpContext ctx) => {
    string uid = ctx.Request.RouteValues["uid"].ToString();
    Console.WriteLine("START: AffiliateInfo uid {0}", uid);

    (double total, int TotaRef,
        double unclm, string joined, int comm) = await FireDB.GetAffiliateInfo(uid);
    if (total == -9.2) {
        Console.WriteLine("{0}. End", joined);
        return Results.Text(joined, statusCode: 281);
    }
    Referent[] arr = await FireDB.GetReferents(uid, TotaRef);
    double share = Math.Round((double)TotaRef/MyEnv.N_users, 2);
    Console.WriteLine("AffiliateInfo End");
    return Results.Json(new AffiData(
        "no error", TotaRef, share, total, unclm, arr, joined, comm
    ));
});

app.Run();