using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
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

    public static readonly HashSet<string> ofs = new HashSet<string>(3) {
        "nick", "earned", "since"
    };

    public static async Task<(string err, Referent[] arr, T lv, bool vm)> GetArray<T>(
        string uid, string OrderField, string OrderDir, T pagi) {
        int ii = 0;
        T LastVal = default(T);
        bool ViewMore = false;
        Console.WriteLine("ii {0} LastVal {1} ViewMore {2}", ii, LastVal, ViewMore);

        Query qu = FireDB.db
            .Collection($"{MyEnv.pfx}users")
            .WhereEqualTo("affiliate.uid", uid);

        if (OrderDir == "Asc") qu = qu.OrderBy($"affiliate.{OrderField}");
        else qu = qu.OrderByDescending($"affiliate.{OrderField}");
        if (pagi != null) {
            try { qu = qu.StartAfter(pagi); }
            catch (Exception ex) {
                Console.WriteLine("Pagination failed: {0}", ex.Message);
                return ("pagination value mismatch", Array.Empty<Referent>(), LastVal, false);
        }}
        QuerySnapshot qs = await qu.Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();
        Console.WriteLine("qCount {0} max {1}", qs.Documents.Count, MyEnv.ReferentQuerySize);
        if (qs.Documents.Count == 0) return (null, Array.Empty<Referent>(), LastVal, false);
        Referent[] arr = new Referent[qs.Documents.Count];

        foreach (DocumentSnapshot doc in qs.Documents) {
            string nick = doc.GetValue<string>("nickname");
            double earn = doc.GetValue<double>("affiliate.earned");
            arr[ii++] = new Referent(
                doc.Id, nick,
                doc.GetValue<string>("photoURI"),
                earn, doc.GetValue<string>("affiliate.since")
            );
            if (ii == MyEnv.ReferentQuerySize) {
                ViewMore = true;
                LastVal = doc.GetValue<T>($"affiliate.{OrderField}");
            }
            Console.WriteLine(
                "Referent {0} Nr {1} nick {2} earned {3}", doc.Id, ii-1, nick, earn);
        }
        Console.WriteLine("RefArray done, ViewMore {0} LastVal {1}", ViewMore, LastVal);
        return (null, arr, LastVal, ViewMore);
    }
}

public class ReferentsJsonResponse<T> {
    public string error {get;}
    public bool ViewMore {get;}
    public T LastValue {get;}
    public Referent[] referents {get;}
    public ReferentsJsonResponse(string er, Referent[] rf, bool vm, T of) {
        error=er; referents=rf; ViewMore=vm; LastValue=of;
}}
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