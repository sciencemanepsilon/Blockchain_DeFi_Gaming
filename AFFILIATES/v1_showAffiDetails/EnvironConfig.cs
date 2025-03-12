using System;

public readonly struct MyEnv {
    public static readonly string pid = System
        .Environment.GetEnvironmentVariable("POJECT_ID");
    public static readonly string pfx = System
        .Environment.GetEnvironmentVariable("DB_COLL_PREFIX");
    public static readonly int N_users = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("N_USERS"));
    public static readonly int ReferentQuerySize = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("REFERENT_QUERY_SIZE"));
    public static readonly int RevenuePercent = Convert.ToInt32(System
        .Environment.GetEnvironmentVariable("REVENUE_PERCENT"));
}