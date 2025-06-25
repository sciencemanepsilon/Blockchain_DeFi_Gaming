using System;
using Google.Cloud.Firestore;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;

public record Better(string Uid, string Aid, string Txid);

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

    public static async Task<AffiDoc> GetAffiliateInfo(string uid) {
        AffiDoc doc;
        try {
            doc = await db.RunTransactionAsync(async tx => {
                DocumentSnapshot ds = await tx.GetSnapshotAsync(
                    db.Collection($"{MyEnv.pfx}affiliates").Document(uid));
                if (!ds.Exists) return new AffiDoc(-9.2, 0, 0.2, "affiliate.uid not exist", 0);
                return new AffiDoc(
                    ds.GetValue<double>("TotalEarned"),
                    ds.GetValue<int>("TotalReferents"),
                    ds.GetValue<double>("Unclaimed"),
                    ds.GetValue<string>("JoinedAt"), ds.GetValue<int>("RevenuePercent")
                );
            });
        } catch (Exception ex) {
            Console.WriteLine("tx failed: {0}", ex.Message);
            doc = new AffiDoc(-9.2, 0, 0.2, "Sorry, we have high traffic. Please try again", 0);
        }
        Console.WriteLine(
            "tx success: TotEarn {0} TotRef {1} unclm {2} joined {3}",
            doc.TotalEarned, doc.TotalReferents, doc.Unclaimed, doc.JoinedAt
        );
        return doc;
    }

    public class AffiDoc {
        public double TotalEarned {get;}
        public int TotalReferents {get;}
        public double Unclaimed {get;}
        public string JoinedAt {get;}
        public int RevenuePercent {get;}
        public AffiDoc(double te, int TotRef, double Unclm, string ja, int RevPercent) {
            TotalEarned=te; TotalReferents=TotRef; Unclaimed=Unclm; JoinedAt=ja; RevenuePercent=RevPercent;
        }
    }
}

public class AffiData<T> {
    public string error {get;}
    public bool ViewMore {get;}
    public T LastValue {get;}
    public int nRefs {get;}
    public double share {get;}
    public double EarnedTotal {get;}
    public double unclaimed {get;}
    public Referent[] referents {get;}
    public string JoinedAt {get;}
    public int RevenuePercent {get;}
    public AffiData(string er, int nr, double sh,
        double et, double un, Referent[] rf, string jo, int rp, bool vm, T of) {
        error=er; nRefs=nr; share=sh;
        EarnedTotal=et; unclaimed=un; referents=rf;
        JoinedAt=jo; RevenuePercent=rp; ViewMore=vm; LastValue=of;
}}
