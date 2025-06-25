using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.Firestore;

public struct ExeClaim {
    public static async Task<(string err, double un)> UpdateUnclaimed(string uid, double vol, double usdval) {
        double ThreeCentAsPOL = 0.002/usdval;
        DocumentReference AffiRef = FireDB.db
            .Collection($"{MyEnv.pfx}affiliates").Document(uid);
        try {
            (string err, double UN) = await FireDB.db.RunTransactionAsync(async tx => {
                Console.WriteLine("starting tx for unclaimed");
                DocumentSnapshot ds = await tx.GetSnapshotAsync(AffiRef);
                if (ds.Exists == false) return ("affiliate.uid not exist", 0);
                double unclm = ds.GetValue<double>("Unclaimed");
                if (vol > unclm + ThreeCentAsPOL) return ("claim amount > unclaimed", 0);
                tx.Update(
                    AffiRef, new Dictionary<string, object>() { {"Unclaimed", unclm - vol} }
                );
                return ("success", unclm);
            });
            Console.WriteLine("result {0} unclaimed {1} POL", err, UN);
            return (err, UN);
        } catch (Exception ex) {
            Console.WriteLine("Tx failed: {0}", ex.Message);
            return ("tx failed", 0);
    }}

    public static async Task<int> RollBackUnclaimed(string uid, double oldUnclaimed) {
        await FireDB.db.Collection($"{MyEnv.pfx}affiliates").Document(uid)
            .UpdateAsync(new Dictionary<string, object>() { {"Unclaimed", oldUnclaimed} });
    
        Console.WriteLine("Unclaimed rolled back to {0}", oldUnclaimed);
        return 0;
    }
    
    public static async Task<int> WriteClaimTx(string uid, string curr, string txh, double uncl) {
        DocumentReference doc = FireDB.db.Collection($"{MyEnv.pfx}affiliateTx").Document();
        await doc.SetAsync(new Dictionary<string, object>() {
            {"Claimer", uid},
            {"Currency", curr},
            {"TxHash", txh},
            {"Amount", uncl},
            {"Date", DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")}
        });
        Console.WriteLine("ClaimTx written, doc.id {0}", doc.Id);
        return 0;
    }
    
    public static async Task<ClaimTx[]> GetClaimTx(string uid) {
        int ii = 0;
        QuerySnapshot qs = await FireDB.db
            .Collection($"{MyEnv.pfx}affiliateTx")
            .WhereEqualTo("Claimer", uid)
            .Limit(499).GetSnapshotAsync();

        Console.WriteLine("ClaimTxQueryCount {0}", qs.Documents.Count);
        ClaimTx[] arr = new ClaimTx[qs.Documents.Count];

        foreach (DocumentSnapshot doc in qs.Documents) {
            arr[ii] = new ClaimTx(
                doc.GetValue<string>("Claimer"),
                doc.GetValue<string>("Date"),
                doc.GetValue<string>("Currency"),
                doc.GetValue<string>("TxHash"), doc.GetValue<double>("Amount")
            );
            Console.WriteLine(
                "Tx {0} Nr {1} curr {2} {3}",
                doc.Id, ii, arr[ii].Currency, arr[ii].Amount
            );
            ii++;
        }
        return arr;
    }
}

public record ClaimTx(
    string Claimer, string Date,
    string Currency, string TxHash, double Amount
);