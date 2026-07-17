namespace SomSkillWorker;

public sealed class KafkaOptions
{
    public string BootstrapServers { get; set; } = "localhost:9092";
    public string GroupId { get; set; } = "nbcu-editorial-standards";
    public string SecurityProtocol { get; set; } = "Plaintext";      // "SaslSsl" for Confluent Cloud
    public string SaslMechanism { get; set; } = "Plain";
    public string SaslUsername { get; set; } = "";                     // Confluent Cloud API key
    public string SaslPassword { get; set; } = "";                     // Confluent Cloud API secret

    // Topics — matches hackathon brief §3.3
    public string StoryContextTopic { get; set; } = "som.story.context";
    public string SkillEventsTopic { get; set; } = "som.skills.events";
    public string SkillRunsTopic { get; set; } = "som.skills.runs";

    // Approval-gating topics for the dashboard
    // SkillWorker publishes outputs to staging; dashboard republishes approved → events, rejected → rejected
    public string SkillStagingTopic { get; set; } = "som.skills.staging";
    public string SkillRejectedTopic { get; set; } = "som.skills.rejected";

    // v0.3.1 distribution layer (§3.3) — TAMS junction, produced by MockMamService
    // until a real MAM/TAMS participant joins. Remaining families (som.link.*,
    // som.telling.*, som.system.audit) are WS1 of the Aug hackathon.
    public string DeliveryTopic { get; set; } = "som.delivery.media_available";

    public string DashboardGroupId { get; set; } = "som-dashboard";
}
