using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;

namespace Lighthouse.Web.Services;

public sealed class ImpactPipelineClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    private readonly HttpClient _httpClient;
    private readonly ImpactMlApiOptions _options;

    public ImpactPipelineClient(HttpClient httpClient, IOptions<ImpactMlApiOptions> options)
    {
        _httpClient = httpClient;
        _options = options.Value;

        if (_httpClient.BaseAddress is null)
        {
            throw new InvalidOperationException("ImpactPipelineClient HttpClient must have BaseAddress configured.");
        }
    }

    /// <summary>GET pipeline overlay from ml-service (public_impact_snapshots pipeline artifact / cache).</summary>
    public async Task<ImpactPipelineInsightsResponse?> GetPipelineInsightsAsync(CancellationToken cancellationToken = default)
    {
        var path = string.IsNullOrWhiteSpace(_options.AnalyticsPath)
            ? "/impact/analytics"
            : _options.AnalyticsPath.TrimStart('/');

        return await _httpClient.GetFromJsonAsync<ImpactPipelineInsightsResponse>(path, JsonOptions, cancellationToken);
    }
}

public sealed class ImpactPipelineInsightsResponse
{
    public string GeneratedAtUtc { get; init; } = "";
    public string PipelineName { get; init; } = "";
    public string DataSource { get; init; } = "";
    public string? Headline { get; init; }
    public string? Summary { get; init; }
    public JsonElement? MetricHighlights { get; init; }
    public string? LoadWarning { get; init; }

    [JsonPropertyName("relatedPipelines")]
    public IReadOnlyList<string>? RelatedPipelines { get; init; }
}
