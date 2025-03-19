using System;
using Google.Cloud.Firestore;
using System.Threading.Tasks;
using System.Collections.Generic;

public record Better(string Uid, string Aid, string Txid);
public record Player(string Uid, string Aid, double TxVol);


class FireDB {
    public static FirestoreDb db = FirestoreDb.Create(MyEnv.pid);

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
    public AffiData(string er, int nr, double sh,
        double et, double un, Referent[] rf, string jo, int rp) {
        error=er; nRefs=nr; share=sh;
        EarnedTotal=et; unclaimed=un; referents=rf;
        JoinedAt=jo; RevenuePercent=rp;
}}
