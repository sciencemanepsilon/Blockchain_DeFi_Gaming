using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;

public class Httpx {
    private static HttpClient hpx = new HttpClient();

    public static async Task<(string ResponseText, int Code)> MakeRequest(
        string url, HttpMethod callMeth, Dictionary<string, string>? headers, object? jsonObj) {
        
        using var request = new HttpRequestMessage(callMeth, url);
        Console.WriteLine("calling {0}", url);

        if (jsonObj != null) {
            var myJs = JsonSerializer.Serialize(jsonObj);
            request.Content = new StringContent(
                myJs, new System.Net.Http.Headers.MediaTypeHeaderValue("application/json")
            );
            Console.WriteLine("JsonString {0}", myJs);
        }
        if (headers != null) {
            foreach (KeyValuePair<string, string> kvp in headers)
                request.Headers.Add(kvp.Key, kvp.Value);
        }
        using HttpResponseMessage res = await hpx.SendAsync(request);
        int rcode = (int)res.StatusCode;
        string ResText = await res.Content.ReadAsStringAsync();
        Console.WriteLine("res {0} int {1} text {2}", res.StatusCode, rcode, ResText);
        return (ResText, rcode);
    }
}