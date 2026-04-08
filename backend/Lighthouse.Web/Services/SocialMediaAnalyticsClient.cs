using System.Net.Http.Headers;
using System.Net.Http.Json;
using Microsoft.Extensions.Options;

namespace Lighthouse.Web.Services;

public class SocialMediaMlApiOptions
{
    public string BaseUrl { get; set; } = "http://localhost:8001";
    public string AnalyticsPath { get; set; } = "/social-media/analytics";
    public string? ApiKey { get; set; }
}

public class SocialMediaAnalyticsClient
{
    private readonly HttpClient _httpClient;
    private readonly SocialMediaMlApiOptions _options;

    public SocialMediaAnalyticsClient(HttpClient httpClient, IOptions<SocialMediaMlApiOptions> options)
    {
        _httpClient = httpClient;
        _options = options.Value;

        if (_httpClient.BaseAddress is null)
        {
            var baseUrl = string.IsNullOrWhiteSpace(_options.BaseUrl)
                ? "http://localhost:8001"
                : _options.BaseUrl.TrimEnd('/');
            _httpClient.BaseAddress = new Uri(baseUrl);
        }

        if (!string.IsNullOrWhiteSpace(_options.ApiKey)
            && !_httpClient.DefaultRequestHeaders.Contains("X-Api-Key"))
        {
            _httpClient.DefaultRequestHeaders.Add("X-Api-Key", _options.ApiKey);
        }

        _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    }

    public async Task<SocialMediaAnalyticsResponse?> GetAnalyticsAsync(CancellationToken cancellationToken = default)
    {
        var path = string.IsNullOrWhiteSpace(_options.AnalyticsPath)
            ? "/social-media/analytics"
            : _options.AnalyticsPath;

        return await _httpClient.GetFromJsonAsync<SocialMediaAnalyticsResponse>(path, cancellationToken);
    }
}

public record SocialMediaAnalyticsResponse(
    string GeneratedAtUtc,
    string Currency,
    SocialMediaSummary Summary,
    IReadOnlyList<SocialMediaPlatformRankingRow> PlatformRanking,
    IReadOnlyList<SocialMediaRecommendationRow> Recommendations,
    IReadOnlyList<SocialMediaPostingWindowRow> BestPostingWindows
);

public record SocialMediaSummary(
    int TotalPosts,
    int TotalDonationReferrals,
    decimal TotalEstimatedDonationValuePhp,
    decimal AvgEngagementRate
);

public record SocialMediaPlatformRankingRow(
    string Platform,
    int Posts,
    int DonationReferrals,
    decimal EstimatedDonationValuePhp,
    decimal AvgEngagementRate,
    decimal ShareOfDonationValue
);

public record SocialMediaRecommendationRow(
    string Platform,
    string Priority,
    string Reason,
    string RecommendedAction,
    IReadOnlyList<string> SuggestedPostHours,
    decimal EstimatedMonthlyLiftPhp
);

public record SocialMediaPostingWindowRow(
    string Platform,
    string DayOfWeek,
    int PostHour,
    decimal AvgDonationValuePhp,
    decimal AvgReferrals
);
