using System;
using System.Collections.Generic;

public readonly struct MyEnv {
    public static readonly string pid = System
        .Environment.GetEnvironmentVariable("POJECT_ID");
    
    public static readonly string pfx = System
        .Environment.GetEnvironmentVariable("DB_COLL_PREFIX");
    
    public static readonly int N_users = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("N_USERS"));
    
    public static readonly int ReferentQuerySize = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("REFERENT_QUERY_SIZE"));
    
    public static readonly double RevenueFactor = Convert.ToDouble(System
        .Environment.GetEnvironmentVariable("REVENUE_PERCENT"))/100;
    
    public static readonly int MinClaim = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("MIN_CLAIM_USD"));
    
    public static readonly string LudoWeb3_URL = System
        .Environment.GetEnvironmentVariable("BLOCKCHAIN_API_LUDO");
    
    public static readonly string LudoWeb3_Route = System
        .Environment.GetEnvironmentVariable("contractFuncRoute");
    
    public static readonly Dictionary<string, TableAtt> Tab = new Dictionary<string, TableAtt>() {
        { "SportBet", new TableAtt(0.05, "Sport Bet") },
        { "pokerCP_Tables", new TableAtt(0.01, "Poker Cash Play") },
        { "pokerTournament_Tables", new TableAtt(0.01, "Poker Tournament") },
        { "BlackJack_Tables", new TableAtt(1.0, "BlackJack") },
        { "LudoClassic_Tables", new TableAtt(0.05, "Ludo Classic") },
        { "LudoTimer_Tables", new TableAtt(0.05, "Ludo Timer") },
        { "LudoMoveableTimer_Tables", new TableAtt(0.05, "Quick Ludo") }
    };
    public static (double, string, string) GetGameAtt(string from) {
        double comm = Tab[from].Com;
        string pretty = Tab[from].Name;
        string dat = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
        Console.WriteLine("com {0} {1}", comm, pretty);
        return (comm, pretty, dat);
    }
}
public record TableAtt(double Com, string Name);