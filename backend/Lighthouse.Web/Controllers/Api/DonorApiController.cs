using System.Security.Claims;
using Lighthouse.Web.Authorization;
using Lighthouse.Web.Models.Identity;
using Lighthouse.Web.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace Lighthouse.Web.Controllers.Api;

[Authorize(Policy = AppPolicies.DonorOnly)]
[Route("api/donor")]
[ApiController]
public class DonorApiController : ControllerBase
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly DonationAnalyticsService _analytics;
    private readonly IDonorPredictionService _prediction;

    public DonorApiController(
        UserManager<ApplicationUser> userManager,
        DonationAnalyticsService analytics,
        IDonorPredictionService prediction)
    {
        _userManager = userManager;
        _analytics = analytics;
        _prediction = prediction;
    }

    [HttpGet("summary")]
    public async Task<IActionResult> Summary(CancellationToken cancellationToken)
    {
        var user = await _userManager.GetUserAsync(User);
        if (user?.SupporterId is null or 0)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var summary = await _analytics.GetDonorSummaryAsync(user.SupporterId.Value, cancellationToken);
        return Ok(summary);
    }

    [HttpGet("donations")]
    public async Task<IActionResult> Donations(CancellationToken cancellationToken)
    {
        var user = await _userManager.GetUserAsync(User);
        if (user?.SupporterId is null or 0)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var monthly = await _analytics.GetMonthlyTotalsAsync(user.SupporterId.Value, cancellationToken);
        return Ok(monthly);
    }

    [HttpGet("prediction")]
    public async Task<IActionResult> Prediction(CancellationToken cancellationToken)
    {
        var user = await _userManager.GetUserAsync(User);
        if (user?.SupporterId is null or 0)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var result = await _prediction.PredictNextDonationLikelihoodAsync(user.SupporterId.Value, cancellationToken);
        return Ok(result);
    }
}
