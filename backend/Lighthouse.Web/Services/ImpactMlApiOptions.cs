namespace Lighthouse.Web.Services;

/// <summary>
/// Optional ML/pipeline overlay for GET /api/impact. Uses the same host as <see cref="SocialMediaMlApiOptions"/> when <see cref="BaseUrl"/> is empty.
/// </summary>
public class ImpactMlApiOptions
{
    /// <summary>When false, only EF aggregates are returned (no HTTP call to ml-service).</summary>
    public bool Enabled { get; set; } = true;

    /// <summary>Base URL of the FastAPI ml-service (e.g. http://localhost:8001). Empty = use SocialMediaMlApi BaseUrl.</summary>
    public string? BaseUrl { get; set; }

    public string AnalyticsPath { get; set; } = "/impact/analytics";
}
