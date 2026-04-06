using System.ComponentModel.DataAnnotations;

namespace Lighthouse.Web.Models.Entities;

public class ProcessRecording
{
    [Key]
    public int RecordingId { get; set; }

    public int ResidentId { get; set; }
    public Resident Resident { get; set; } = null!;

    public DateOnly SessionDate { get; set; }

    [MaxLength(20)]
    public string SocialWorker { get; set; } = string.Empty;

    [MaxLength(20)]
    public string SessionType { get; set; } = string.Empty;

    public int? SessionDurationMinutes { get; set; }

    [MaxLength(20)]
    public string? EmotionalStateObserved { get; set; }
    [MaxLength(20)]
    public string? EmotionalStateEnd { get; set; }

    public string? SessionNarrative { get; set; }
    public string? InterventionsApplied { get; set; }
    public string? FollowUpActions { get; set; }

    public bool ProgressNoted { get; set; }
    public bool ConcernsFlagged { get; set; }
    public bool ReferralMade { get; set; }

    public bool NotesRestricted { get; set; }
}
