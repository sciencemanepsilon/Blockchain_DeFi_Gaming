using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.Firestore;


public struct Referents {
    public static async Task<(string err, ReferentTx[] arr, bool vm)> GetTxArray(string uid, string pagi) {
        int ii = 0;
        bool ViewMore = false;
        
        Query qu = FireDB.db
            .Collection($"{MyEnv.pfx}affiliateTx")
            .WhereEqualTo("Referent", uid)
            .OrderByDescending("Date");
        
        if (pagi != null) {
            try { qu = qu.StartAfter(pagi); }
            catch (Exception ex) {
                Console.WriteLine("Pagination failed: {0}", ex.Message);
                return ("pagination value mismatch", Array.Empty<ReferentTx>(), false);
        }}
        QuerySnapshot qs = await qu.Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();
        Console.WriteLine("TxQueryCount {0}", qs.Documents.Count);
        if (qs.Documents.Count == 0) return (null, Array.Empty<ReferentTx>(), false);
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
            if (ii == MyEnv.ReferentQuerySize) ViewMore = true;
            Console.WriteLine(
                "Tx {0} Nr {1} vol {2} rev {3} from", doc.Id, ii-1, vol, rev, from);
        }
        Console.WriteLine("RefTx done, ViewMore {0}", ViewMore);
        return (null, arr, ViewMore);
    }


    public static async Task<(string err, Referent[] arr, double? lv1, string lv2, bool vm)> GetArray(
        string uid, double? pagi1, string pagi2) {
        int ii = 0;
        double? LastVal1 = null;
        string LastVal2 = null;
        bool ViewMore = false;
        Console.WriteLine("ii {0} ViewMore {1}", ii, ViewMore);

        Query qu = FireDB.db
            .Collection($"{MyEnv.pfx}users")
            .WhereEqualTo("affiliate.uid", uid)
            .OrderByDescending("affiliate.earned")
            .OrderByDescending("nickname");
        
        if (pagi1 != null && pagi2 != null) {
            try { qu = qu.StartAfter(pagi1, pagi2); }
            catch (Exception ex) {
                Console.WriteLine("Pagination failed: {0}", ex.Message);
                return ("pagination value mismatch", Array.Empty<Referent>(), LastVal1, LastVal2, false);
        }}
        QuerySnapshot qs = await qu.Limit(MyEnv.ReferentQuerySize).GetSnapshotAsync();
        Console.WriteLine("qCount {0} max {1}", qs.Documents.Count, MyEnv.ReferentQuerySize);
        if (qs.Documents.Count == 0) return (null, Array.Empty<Referent>(), LastVal1, LastVal2, false);
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
                LastVal1 = earn;
                LastVal2 = nick;
            }
            Console.WriteLine(
                "Referent {0} Nr {1} nick {2} earned {3}", doc.Id, ii-1, nick, earn);
        }
        Console.WriteLine("RefArray done, ViewMore {0} lv1 {1} lv2 {2}", ViewMore, LastVal1, LastVal2);
        return (null, arr, LastVal1, LastVal2, ViewMore);
    }
}

public class ReferentsJsonResponse {
    public string error {get;}
    public bool ViewMore {get;}
    public double? LastValue1 {get;}
    public string LastValue2 {get;}
    public Referent[] referents {get;}
    public ReferentsJsonResponse(string er, Referent[] rf, bool vm, double? lv1, string lv2) {
        error=er; referents=rf; ViewMore=vm; LastValue1=lv1; LastValue2=lv2;
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