namespace SomSkillWorker;

/// <summary>
/// Envelope <c>som_version</c> = the schema pack version payloads conform to.
/// The SOM-048 "0.2.0 wire freeze" was retired 12 Aug 2026 — the field now says
/// what pack you are on. Informative only; <c>message_type</c> identifies the
/// payload family, and no consumer may branch on this value to parse.
/// </summary>
public static class SomEnvelope
{
    public const string Version = "0.3.2";
}
