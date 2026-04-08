using System.Security.Claims;
using Lighthouse.Web.Authorization;
using Lighthouse.Web.Data;
using Lighthouse.Web.Models.Entities;
using Lighthouse.Web.Models.Identity;
using Lighthouse.Web.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace Lighthouse.Web.Controllers.Api;

[Authorize(Policy = AppPolicies.DonorOnly)]
[Route("api/donor")]
[ApiController]
public class DonorApiController : ControllerBase
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly ApplicationDbContext _db;
    private readonly DonationAnalyticsService _analytics;
    private readonly IDonorPredictionService _prediction;

    public DonorApiController(
        UserManager<ApplicationUser> userManager,
        ApplicationDbContext db,
        DonationAnalyticsService analytics,
        IDonorPredictionService prediction)
    {
        _userManager = userManager;
        _db = db;
        _analytics = analytics;
        _prediction = prediction;
    }

    [HttpGet("summary")]
    public async Task<IActionResult> Summary(CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var summary = await _analytics.GetDonorSummaryAsync(supporterId.Value, cancellationToken);
        return Ok(summary);
    }

    [HttpGet("donations")]
    public async Task<IActionResult> Donations(CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var monthly = await _analytics.GetMonthlyTotalsAsync(supporterId.Value, cancellationToken);
        return Ok(monthly);
    }

    [HttpGet("history")]
    public async Task<IActionResult> History(CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var rows = await _analytics.GetDonationHistoryAsync(supporterId.Value, cancellationToken);
        return Ok(rows);
    }

    [HttpGet("prediction")]
    public async Task<IActionResult> Prediction(CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var result = await _prediction.PredictNextDonationLikelihoodAsync(supporterId.Value, cancellationToken);
        return Ok(result);
    }

    public record DonorDonateRequest(decimal Amount, string? Notes, bool IsRecurring);
    public record RecurringDonationRow(int DonationId, string DonationDate, decimal Amount, string? Notes, string? CurrencyCode, DateTimeOffset CreatedAt);
    public record UpdateRecurringDonationRequest(decimal Amount, string? Notes);

    [HttpPost("donate")]
    public async Task<IActionResult> Donate([FromBody] DonorDonateRequest req, CancellationToken cancellationToken)
    {
        if (req.Amount <= 0)
            return BadRequest(new { error = "Amount must be greater than zero." });

        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var priorStats = await _db.Donations
            .AsNoTracking()
            .Where(d => d.SupporterId == supporterId.Value)
            .GroupBy(_ => 1)
            .Select(g => new
            {
                Count = g.Count(),
                Total = g.Sum(x => x.Amount ?? x.EstimatedValue ?? 0m)
            })
            .FirstOrDefaultAsync(cancellationToken);

        var previousDonationCount = priorStats?.Count ?? 0;
        var previousTotal = priorStats?.Total ?? 0m;

        var donorName = await _db.Supporters
            .AsNoTracking()
            .Where(s => s.SupporterId == supporterId.Value)
            .Select(s => s.FirstName ?? s.DisplayName)
            .FirstOrDefaultAsync(cancellationToken);

        var donation = new Donation
        {
            SupporterId = supporterId.Value,
            DonationType = DonationType.Monetary,
            DonationDate = DateOnly.FromDateTime(DateTime.UtcNow),
            IsRecurring = req.IsRecurring,
            ChannelSource = ChannelSource.Direct,
            CurrencyCode = "USD",
            Amount = req.Amount,
            EstimatedValue = req.Amount,
            ImpactUnit = ImpactUnit.pesos,
            Notes = req.Notes?.Trim(),
            CreatedAt = DateTimeOffset.UtcNow
        };

        _db.Donations.Add(donation);
        await _db.SaveChangesAsync(cancellationToken);

        var currentTotal = previousTotal + req.Amount;
        var message = BuildMilestoneMessage(donorName, previousDonationCount, previousTotal, currentTotal);

        return Created(string.Empty, new { donationId = donation.DonationId, message });
    }

    private static string BuildMilestoneMessage(string? donorName, int previousDonationCount, decimal previousTotal, decimal currentTotal)
    {
        var normalizedName = string.IsNullOrWhiteSpace(donorName) ? "Donor" : donorName.Trim();

        // Priority rule: first donation message always wins, even if donation crosses monetary thresholds.
        if (previousDonationCount == 0)
        {
            return $"Thank you for your very first donation, {normalizedName}! Your support means so much to us.";
        }

        var milestones = new[] { 10000m, 5000m, 1000m, 100m };
        var crossed = milestones.FirstOrDefault(m => previousTotal < m && currentTotal >= m);
        if (crossed > 0)
        {
            return crossed switch
            {
                100m => $"Thank you, {normalizedName}! You just crossed $100 in total giving. Your generosity is already creating impact.",
                1000m => $"Amazing, {normalizedName}! You just crossed $1,000 in total giving. Thank you for standing with us in a big way.",
                5000m => $"Incredible milestone, {normalizedName}! You have now given over $5,000. Your commitment is changing lives.",
                10000m => $"Extraordinary generosity, {normalizedName}! You have surpassed $10,000 in total giving. We are deeply grateful for your partnership.",
                _ => $"Thank you, {normalizedName}, for your donation!"
            };
        }

        return $"Thank you, {normalizedName}! Your donation was recorded successfully.";
    }

    [HttpGet("recurring-donations")]
    public async Task<IActionResult> RecurringDonations(CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var rows = await _db.Donations
            .AsNoTracking()
            .Where(d => d.SupporterId == supporterId.Value && d.IsRecurring)
            .OrderByDescending(d => d.CreatedAt)
            .Select(d => new RecurringDonationRow(
                d.DonationId,
                d.DonationDate.ToString("yyyy-MM-dd"),
                d.Amount ?? d.EstimatedValue ?? 0m,
                d.Notes,
                d.CurrencyCode,
                d.CreatedAt))
            .ToListAsync(cancellationToken);

        return Ok(rows);
    }

    [HttpPut("recurring-donations/{donationId:int}")]
    public async Task<IActionResult> UpdateRecurringDonation(int donationId, [FromBody] UpdateRecurringDonationRequest req, CancellationToken cancellationToken)
    {
        if (req.Amount <= 0)
            return BadRequest(new { error = "Amount must be greater than zero." });

        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var donation = await _db.Donations.FirstOrDefaultAsync(
            d => d.DonationId == donationId && d.SupporterId == supporterId.Value,
            cancellationToken);

        if (donation is null)
            return NotFound(new { error = "Recurring donation not found." });
        if (!donation.IsRecurring)
            return BadRequest(new { error = "Only recurring donations can be edited from this view." });

        donation.Amount = req.Amount;
        donation.EstimatedValue = req.Amount;
        donation.Notes = req.Notes?.Trim();
        await _db.SaveChangesAsync(cancellationToken);

        return Ok(new { message = "Recurring donation updated." });
    }

    [HttpDelete("recurring-donations/{donationId:int}")]
    public async Task<IActionResult> DeleteRecurringDonation(int donationId, CancellationToken cancellationToken)
    {
        var supporterId = await ResolveSupporterIdAsync(cancellationToken);
        if (supporterId is null)
            return BadRequest(new { error = "Donor account is not linked to a supporter record." });

        var donation = await _db.Donations.FirstOrDefaultAsync(
            d => d.DonationId == donationId && d.SupporterId == supporterId.Value,
            cancellationToken);

        if (donation is null)
            return NotFound(new { error = "Recurring donation not found." });
        if (!donation.IsRecurring)
            return BadRequest(new { error = "Only recurring donations can be deleted from this view." });

        _db.Donations.Remove(donation);
        await _db.SaveChangesAsync(cancellationToken);
        return NoContent();
    }

    private async Task<int?> ResolveSupporterIdAsync(CancellationToken cancellationToken)
    {
        var user = await _userManager.GetUserAsync(User);
        if (user is null)
            return null;

        if (user.SupporterId is > 0)
            return user.SupporterId.Value;

        if (string.IsNullOrWhiteSpace(user.Email))
            return null;

        var email = user.Email.Trim().ToLowerInvariant();
        var supporterId = await _db.Supporters
            .AsNoTracking()
            .Where(s => s.Email != null && s.Email.ToLower() == email)
            .Select(s => (int?)s.SupporterId)
            .FirstOrDefaultAsync(cancellationToken);

        if (supporterId is null)
            return null;

        // Persist the discovered link so future calls are direct.
        user.SupporterId = supporterId.Value;
        await _userManager.UpdateAsync(user);
        return supporterId.Value;
    }
}
