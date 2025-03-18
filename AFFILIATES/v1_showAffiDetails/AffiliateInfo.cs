using System;
using Google.Cloud.Firestore;
using System.Threading.Tasks;
using System.Collections.Generic;

public record Better(string Uid, string Aid, string Txid);
public record Player(string Uid, string Aid, double TxVol);


class FireDB {
    private static FirestoreDb db = FirestoreDb.Create(MyEnv.pid);


    public static async Task<bool> RunTx(double TxVol, double comm, string Aid,
        string Uid, string txid, string dat, string currency, string pretty, string txh) {
        
        double YourRev = TxVol *comm *MyEnv.RevenueFactor;
        double OurRev = TxVol *comm - YourRev;
        DocumentReference AffiRef = db.Collection($"{MyEnv.pfx}affiliates").Document(Aid);
        DocumentReference PlayerRef = db.Collection($"{MyEnv.pfx}users").Document(Uid);

        bool complete = await db.RunTransactionAsync(async tx => {

            Console.WriteLine("tx start, pl {0} {1}POL AffiRev {2}", Uid, TxVol, YourRev);
            DocumentSnapshot ds = await tx.GetSnapshotAsync(AffiRef);
            double TotEarn = ds.GetValue<double>("TotalEarned") + YourRev;
            double unclm = ds.GetValue<double>("Unclaimed") + YourRev;

            ds = await tx.GetSnapshotAsync(PlayerRef);
            double earned = ds.GetValue<double>("affiliate.earned") + YourRev;
            Console.WriteLine("TotEarn {0} unclm {1} earned {2}", TotEarn, unclm, earned);
            tx.Update(
                AffiRef,
                new Dictionary<string, object>() { {"TotalEarned", TotEarn}, {"Unclaimed", unclm} }
            );
            tx.Update(
                PlayerRef, new Dictionary<string, object>() { {"affiliate.earned", earned} }
            );
            tx.Set(
                db.Collection($"{MyEnv.pfx}affiliateTx").Document(txid),
                new Dictionary<string, object>() {
                    {"Referent", Uid},
                    {"Affiliate", Aid},
                    {"Date", dat},
                    {"Currency", currency},
                    {"From", pretty},
                    {"TxHash", txh},
                    {"TxVolume", TxVol},
                    {"OurRevenue", OurRev},
                    {"YourRevenue", YourRev}
            });
            return true;
        });
        Console.WriteLine("Tx complete {0} pl {0} aid {1}, next iteration", complete, Uid, Aid);
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
                "Tx {0} Nr {1} nick {2} earned {3}", doc.Id, ii-1, nick, earn);
        }
        return arr;
    }
    
    public static async Task<ReferentTx[]> ReferentTx(string uid) {
        int ii = 0;
        QuerySnapshot qs = await db
            .Collection($"{MyEnv.pfx}affiliateTx")
            .WhereEqualTo("Referent", uid)
            .Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();

        Console.WriteLine("TxQueryCount {0}", qs.Documents.Count);
        ReferentTx[] arr = new ReferentTx[qs.Documents.Count];

        foreach (DocumentSnapshot doc in qs.Documents) {
            string from = doc.GetValue<string>("From");
            double rev = doc.GetValue<double>("YourRevenue");
            double vol = doc.GetValue<double>("TxVolume");
            arr[ii++] = new ReferentTx(
                doc.GetValue<string>("Referent"),
                doc.GetValue<string>("Affiliate"),
                doc.GetValue<string>("Date"),
                doc.GetValue<string>("Currency"),
                from, doc.GetValue<string>("TxHash"),
                vol, doc.GetValue<double>("OurRevenue"), rev
            );
            Console.WriteLine(
                "Tx {0} Nr {1} vol {2} rev {3} from", doc.Id, ii-1, vol, rev, from);
        }
        return arr;
    }

    public static async Task<ClaimTx[]> GetClaimTx(string uid) {
        int ii = 0;
        QuerySnapshot qs = await db
            .Collection($"{MyEnv.pfx}affiliateTx")
            .WhereEqualTo("Claimer", uid)
            .Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();

        Console.WriteLine("ClaimTxQueryCount {0}", qs.Documents.Count);
        ClaimTx[] arr = new ClaimTx[qs.Documents.Count];

        foreach (DocumentSnapshot doc in qs.Documents) {
            arr[ii] = doc.ConvertTo<ClaimTx>();
            Console.WriteLine(
                "Tx {0} Nr {1} curr {2} {3}",
                doc.Id, ii, arr[ii].Currency, arr[ii].Amount
            );
            ii += 1;
        }
        return arr;
    }
}
public record ClaimTx(
    string Claimer, string Date,
    string Currency, string TxHash, double Amount
);
public record ReferentTx(
    string Referent, string Affiliate,
    string Date, string Currency, string From,
    string TxHash, double TxVolume, double OurRevenue, double YourRevenue
);
public class AffiData {
    public string error {get;}
    public int nRefs {get;}
    public double share {get;}
    public double EarnedTotal {get;}
    public double unclaimed {get;}
    public Referent[] referents {get;}
    public string JoinedAt {get;}
    public int RevenuePercent {get;}
    public AffiData(string er, int nr, double sh,
        double et, double un, Referent[] rf, string jo, int rp) {
        error=er; nRefs=nr; share=sh;
        EarnedTotal=et; unclaimed=un; referents=rf;
        JoinedAt=jo; RevenuePercent=rp;
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