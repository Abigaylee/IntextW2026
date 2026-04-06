using System.ComponentModel.DataAnnotations;

namespace Lighthouse.Web.Models.Entities;

public class Supporter
{
    public int SupporterId { get; set; }

    [MaxLength(40)]
    public string SupporterType { get; set; } = string.Empty;

    [MaxLength(150)]
    public string DisplayName { get; set; } = string.Empty;

    [MaxLength(150)]
    public string? OrganizationName { get; set; }

    [MaxLength(75)]
    public string? FirstName { get; set; }

    [MaxLength(75)]
    public string? LastName { get; set; }

    [MaxLength(30)]
    public string RelationshipType { get; set; } = string.Empty;

    [MaxLength(20)]
    public string? Region { get; set; }

    [MaxLength(50)]
    public string Country { get; set; } = "Philippines";

    [MaxLength(255)]
    public string? Email { get; set; }

    [MaxLength(30)]
    public string? Phone { get; set; }

    [MaxLength(20)]
    public string Status { get; set; } = "Active";

    public DateTimeOffset CreatedAt { get; set; }

    public DateOnly? FirstDonationDate { get; set; }

    [MaxLength(30)]
    public string? AcquisitionChannel { get; set; }

    public ICollection<Donation> Donations { get; set; } = new List<Donation>();
}
