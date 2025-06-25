using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.Firestore;

public struct ExeClaim {
    public static async Task<string> UpdateUnclaimed(string uid, double vol, double usdval) {
        string err;
        double ThreeCentAsPOL = 0.03/usdval;
        DocumentReference AffiRef = FireDB.db
            .Collection($"{MyEnv.pfx}affiliates").Document(uid);
        try {
            err = await FireDB.db.RunTransactionAsync(async tx => {
                Console.WriteLine("starting tx for unclaimed");
                DocumentSnapshot ds = await tx.GetSnapshotAsync(AffiRef);
                if (ds.Exists == false) return "affiliate.uid not exist";
                double unclm = ds.GetValue<double>("Unclaimed");
                if (vol > unclm + ThreeCentAsPOL) return "claim amount > unclaimed";
                tx.Update(
                    AffiRef, new Dictionary<string, object>() { {"Unclaimed", 0.0} }
                );
                return "success";
            });
        } catch (Exception ex) {
            err = "tx failed";
            Console.WriteLine("Tx failed: {0}", ex);
        }
        Console.WriteLine("result {0}", err);
        return err;
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