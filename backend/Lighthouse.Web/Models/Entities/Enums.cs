using NpgsqlTypes;

namespace Lighthouse.Web.Models.Entities;

public enum SupporterType
{
    [PgName("MonetaryDonor")] MonetaryDonor,
    [PgName("InKindDonor")] InKindDonor,
    [PgName("Volunteer")] Volunteer,
    [PgName("SkillsContributor")] SkillsContributor,
    [PgName("SocialMediaAdvocate")] SocialMediaAdvocate,
    [PgName("PartnerOrganization")] PartnerOrganization
}

public enum RelationshipType
{
    [PgName("Local")] Local,
    [PgName("International")] International,
    [PgName("PartnerOrganization")] PartnerOrganization
}

public enum SupporterStatus
{
    [PgName("Active")] Active,
    [PgName("Inactive")] Inactive
}

public enum AcquisitionChannel
{
    [PgName("SocialMedia")] SocialMedia,
    [PgName("Website")] Website,
    [PgName("Event")] Event,
    [PgName("Church")] Church,
    [PgName("WordOfMouth")] WordOfMouth,
    [PgName("PartnerReferral")] PartnerReferral
}

public enum DonationType
{
    [PgName("Monetary")] Monetary,
    [PgName("InKind")] InKind,
    [PgName("Time")] Time,
    [PgName("Skills")] Skills,
    [PgName("SocialMedia")] SocialMedia
}

public enum ChannelSource
{
    [PgName("Direct")] Direct,
    [PgName("Campaign")] Campaign,
    [PgName("Event")] Event,
    [PgName("SocialMedia")] SocialMedia,
    [PgName("PartnerReferral")] PartnerReferral
}

public enum ImpactUnit
{
    [PgName("pesos")] pesos,
    [PgName("hours")] hours,
    [PgName("items")] items,
    [PgName("campaigns")] campaigns
}

public enum PhRegion { NCR, CAR, RegionI, RegionII, RegionIII, RegionIVA, RegionIVB, RegionV, RegionVI, RegionVII, RegionVIII, RegionIX, RegionX, RegionXI, RegionXII, RegionXIII, BARMM }
