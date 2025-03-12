using System;
using Google.Cloud.Firestore;
using System.Threading.Tasks;
using System.Collections.Generic;

class FireDB {
    private static FirestoreDb db = FirestoreDb.Create(MyEnv.pid);

    public static async Task<bool> CreateAffiliateRecord(string uid) {
        await db.Collection($"{MyEnv.pfx}affiliates")
            .Document(uid).SetAsync(new Dictionary<string, object> {
            {"TotalEarned", 0.0},
            {"TotalReferents", 1},
            {"JoinedAt", DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")},
            {"Unclaimed", 0.0},
            {"RevenuePercent", MyEnv.RevenuePercent}
        });
        return true;
    }
    
    public static async Task<(double, int, double, string, int)> GetAffiliateInfo(string uid) {
        return await db.RunTransactionAsync(async tx => {
            DocumentSnapshot ds = await tx.GetSnapshotAsync(
                db.Collection($"{MyEnv.pfx}affiliates").Document(uid)
            );
            if (!ds.Exists) return (-9.2, 0, 0.2, "affiliate.uid not exist", 0);
            double total = ds.GetValue<double>("TotalEarned");
            int TotalReferents = ds.GetValue<int>("TotalReferents");
            double unclm = ds.GetValue<double>("Unclaimed");
            string joined = ds.GetValue<string>("JoinedAt");
            int comm = ds.GetValue<int>("RevenuePercent");
            Console.WriteLine(
                "ds.GetValue: TotEarn {0} TotRef {1} unclm {2}",
                total, TotalReferents, unclm
            );
            return (total, TotalReferents, unclm, joined, comm);
        });
    }
    public static async Task<Referent[]> GetReferents(string uid, int TotRef) {
        if (TotRef == 0) return Array.Empty<Referent>();
        int ii = 0;
        QuerySnapshot qs = await db
            .Collection($"{MyEnv.pfx}users")
            .WhereEqualTo("affiliate.uid", uid)
            .Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();

        Console.WriteLine("ReferentsQueryCount {0}", qs.Documents.Count);
        Referent[] arr = new Referent[qs.Documents.Count];

        foreach (DocumentSnapshot doc in qs.Documents) {
            string nick = doc.GetValue<string>("nickname");
            double earn = doc.GetValue<double>("affiliate.earned");
            arr[ii++] = new Referent(
                doc.Id, nick,
                doc.GetValue<string>("photoURI"),
                earn, doc.GetValue<string>("affiliate.since")
            );
            Console.WriteLine(
                "referent {0} Nr {1} nick {2} earned {3}", doc.Id, ii-1, nick, earn);
        }
        return arr;
    }
}
public class AffiData {
    public string error {get;}
    public int nRefs {get;}
    public double share {get;}
    public double EarnedTotal {get;}
    public double unclaimed {get;}
    public Referent[] referents {get;}
    public string JoinedAt {get;}
    public int RevenuePercent {get;}
    public AffiData(string er, int nr,
        double sh, double et, double un, Referent[] rf, string jo, int rp) {
        error=er; nRefs=nr; share=sh; EarnedTotal=et;
        unclaimed=un; referents=rf; JoinedAt=jo; RevenuePercent=rp;
}}
public class Referent {
    public string uid {get;}
    public string nick {get;}
    public string photo {get;}
    public double earned {get;}
    public string since {get;}
    public Referent(string ui, string ni, string ph, double ea, string si) {
        uid=ui; nick=ni; photo=ph; earned=ea; since=si;
}}