using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.Firestore;


public struct Referents {
    public static async Task<ReferentTx[]> GetTxArray(string uid) {
        int ii = 0;
        QuerySnapshot qs = await FireDB.db
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

    public static async Task<Referent[]> GetArray(string uid, int TotRef) {
        if (TotRef == 0) return Array.Empty<Referent>();
        int ii = 0;
        QuerySnapshot qs = await FireDB.db
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
}

public record ReferentTx(
    string Referent, string Affiliate,
    string Date, string Currency, string From,
    string TxHash, double TxVolume, double OurRevenue, double YourRevenue
);

public class Referent {
    public string uid {get;}
    public string nick {get;}
    public string photo {get;}
    public double earned {get;}
    public string since {get;}
    public Referent(string ui, string ni, string ph, double ea, string si) {
        uid=ui; nick=ni; photo=ph; earned=ea; since=si;
}}