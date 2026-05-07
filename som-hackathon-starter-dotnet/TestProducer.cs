using System.Text.Json;
using System.Text.Json.Nodes;
using Confluent.Kafka;

namespace SomSkillWorker;

/// <summary>
/// Publishes seed story.context messages to som.story.context for local testing.
///
/// Usage:
///   dotnet run -- --test-producer                                  → publishes all seed stories
///   dotnet run -- --test-producer --story breaking                 → single scenario
///   dotnet run -- --test-producer --story informal
///   dotnet run -- --test-producer --story election
///   dotnet run -- --test-producer --story clean
///   dotnet run -- --test-producer --story breaking-no-compliance
///
/// Seed stories live in ./seed-stories/*.json — full SOM v0.2 story.context payloads.
/// </summary>
public static class TestProducer
{
    private static readonly Dictionary<string, string> ScenarioFiles = new(StringComparer.OrdinalIgnoreCase)
    {
        ["breaking"]                = "seed-stories/01-breaking-courthouse.json",
        ["election"]                = "seed-stories/02-developing-election.json",
        ["informal"]                = "seed-stories/03-informal-headline.json",
        ["clean"]                   = "seed-stories/04-clean-transit.json",
        ["breaking-no-compliance"]  = "seed-stories/05-breaking-no-compliance.json",
    };

    /// <summary>Available scenarios in the order they should appear in the UI.</summary>
    public static IReadOnlyList<string> Scenarios => ScenarioFiles.Keys.ToArray();

    /// <summary>
    /// Returns the raw SOM v0.2 envelope JSON for a given scenario, or null if unknown.
    /// </summary>
    public static async Task<string?> LoadScenarioJsonAsync(string scenario)
    {
        if (!ScenarioFiles.TryGetValue(scenario, out var relPath)) return null;
        var path = ResolveSeedPath(relPath);
        return path is null ? null : await File.ReadAllTextAsync(path);
    }

    private static string? ResolveSeedPath(string relPath)
    {
        var primary = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", relPath);
        if (File.Exists(primary)) return primary;
        if (File.Exists(relPath)) return relPath;
        return null;
    }

    public static async Task RunAsync(string? scenario = null)
    {
        var bootstrapServers = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP_SERVERS") ?? "localhost:9092";
        var topic = Environment.GetEnvironmentVariable("KAFKA_STORY_CONTEXT_TOPIC") ?? "som.story.context";

        var config = new ProducerConfig
        {
            BootstrapServers = bootstrapServers,
            Acks = Acks.Leader,
        };

        // Support Confluent Cloud (SaslSsl) when env vars are set
        var apiKey = Environment.GetEnvironmentVariable("KAFKA_API_KEY");
        var apiSecret = Environment.GetEnvironmentVariable("KAFKA_API_SECRET");
        if (!string.IsNullOrEmpty(apiKey) && !string.IsNullOrEmpty(apiSecret))
        {
            config.SecurityProtocol = SecurityProtocol.SaslSsl;
            config.SaslMechanism = SaslMechanism.Plain;
            config.SaslUsername = apiKey;
            config.SaslPassword = apiSecret;
        }

        using var producer = new ProducerBuilder<string, string>(config).Build();

        // If no scenario specified, publish all seed stories
        var scenarios = scenario is null
            ? ScenarioFiles.Keys.ToList()
            : new List<string> { scenario };

        foreach (var name in scenarios)
        {
            if (!ScenarioFiles.TryGetValue(name, out var filePath))
            {
                Console.WriteLine($"Unknown scenario '{name}'. Available: {string.Join(", ", ScenarioFiles.Keys)}");
                continue;
            }

            var fullPath = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", filePath);
            if (!File.Exists(fullPath))
            {
                // Fallback: try relative to current directory
                fullPath = filePath;
            }

            if (!File.Exists(fullPath))
            {
                Console.WriteLine($"Seed file not found: {filePath}");
                continue;
            }

            var json = await File.ReadAllTextAsync(fullPath);
            var envelope = JsonNode.Parse(json);
            if (envelope is null)
            {
                Console.WriteLine($"Failed to parse {filePath}");
                continue;
            }

            // Extract story_id from payload for the Kafka key
            var storyId = envelope["payload"]?["story_id"]?.GetValue<string>() ?? "unknown";

            // The skill worker consumes the payload (story context), not the full envelope.
            // Publish just the payload to match what the worker expects.
            var payload = envelope["payload"];
            if (payload is null)
            {
                Console.WriteLine($"No payload in {filePath}");
                continue;
            }

            var payloadJson = payload.ToJsonString();

            Console.WriteLine($"─── {name.ToUpperInvariant()} ───");
            Console.WriteLine($"  Story:    {storyId}");
            Console.WriteLine($"  Headline: {payload["headline"]?.GetValue<string>()}");
            Console.WriteLine($"  Phase:    {payload["lifecycle"]?["phase"]?.GetValue<string>()}");
            Console.WriteLine($"  File:     {filePath}");

            var result = await producer.ProduceAsync(topic, new Message<string, string>
            {
                Key = storyId,
                Value = payloadJson,
            });

            Console.WriteLine($"  → Partition {result.Partition.Value}, Offset {result.Offset.Value}");
            Console.WriteLine();
        }

        Console.WriteLine("Done. Your skill worker should pick these up.");
    }
}
