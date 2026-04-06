using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Lighthouse.Web.Models.Entities;

public class Donation
{
    public int DonationId { get; set; }

    public int SupporterId { get; set; }
    public Supporter Supporter { get; set; } = null!;

    [MaxLength(30)]
    public string DonationType { get; set; } = string.Empty;

    public DateOnly DonationDate { get; set; }

    public bool IsRecurring { get; set; }

    [MaxLength(150)]
    public string? CampaignName { get; set; }

    [MaxLength(30)]
    public string? ChannelSource { get; set; }

    [MaxLength(3)]
    public string? CurrencyCode { get; set; }

    [Column(TypeName = "numeric(12,2)")]
    public decimal? Amount { get; set; }

    [Column(TypeName = "numeric(12,2)")]
    public decimal? EstimatedValue { get; set; }

    [MaxLength(20)]
    public string? ImpactUnit { get; set; }

    public string? Notes { get; set; }

    public int? ReferralPostId { get; set; }

    public DateTimeOffset CreatedAt { get; set; }

    public ICollection<DonationAllocation> DonationAllocations { get; set; } = new List<DonationAllocation>();
    public ICollection<InKindDonationItem> InKindDonationItems { get; set; } = new List<InKindDonationItem>();
}
