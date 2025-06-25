using System;
using System.Collections.Generic;

public readonly struct MyEnv {
    public static readonly string pid = System
        .Environment.GetEnvironmentVariable("POJECT_ID");
    
    public static readonly string pfx = System
        .Environment.GetEnvironmentVariable("DB_COLL_PREFIX");
    
    public static readonly int N_users = Convert
        .ToInt32(System.Environment.GetEnvironmentVariable("N_USERS"));
    
    public static readonly int ReferentQuerySize = Convert
        .ToInt32(System.Environment.GetEnvironmentVariable("REFERENT_QUERY_SIZE"));
    
    public static readonly double RevenueFactor = Convert
        .ToDouble(System.Environment.GetEnvironmentVariable("REVENUE_PERCENT"))/100;
    
    public static readonly int MinClaim = Convert
        .ToInt32(System.Environment.GetEnvironmentVariable("MIN_CLAIM_USD"));
    
    public static readonly string LudoWeb3_URL = System
        .Environment.GetEnvironmentVariable("BLOCKCHAIN_API_LUDO");
    
    public static readonly string LudoWeb3_Route = System
        .Environment.GetEnvironmentVariable("contractFuncRoute");
    
    public static readonly double SportBetComm = Convert
        .ToDouble(System.Environment.GetEnvironmentVariable("SPORT_BET_COMM"));
}