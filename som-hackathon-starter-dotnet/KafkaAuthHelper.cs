using Confluent.Kafka;
using System;

namespace SomSkillWorker;

internal static class KafkaAuthHelper
{
    public static void Configure(ClientConfig config, KafkaOptions options)
    {
        if (Enum.TryParse<SecurityProtocol>(options.SecurityProtocol, true, out var sp))
        {
            config.SecurityProtocol = sp;
        }

        if (Enum.TryParse<SaslMechanism>(options.SaslMechanism, true, out var sm))
        {
            config.SaslMechanism = sm;
        }

        // Only SASL protocols need credentials.
        var isSasl = options.SecurityProtocol.StartsWith("Sasl", StringComparison.OrdinalIgnoreCase);
        if (!isSasl) return;

        // SaslSsl + Plain is the GCP Managed Kafka path: username is the SA email,
        // password is a short-lived ADC access token.
        var isGcpManagedKafka = options.SecurityProtocol.Equals("SaslSsl", StringComparison.OrdinalIgnoreCase)
                             && options.SaslMechanism.Equals("Plain", StringComparison.OrdinalIgnoreCase);

        if (isGcpManagedKafka)
        {
            config.SaslUsername = Environment.GetEnvironmentVariable("WorkerSaEmail") ?? options.SaslUsername;
            var credential = Google.Apis.Auth.OAuth2.GoogleCredential.GetApplicationDefaultAsync().GetAwaiter().GetResult();
            if (credential.IsCreateScopedRequired)
            {
                credential = credential.CreateScoped(new[] { "https://www.googleapis.com/auth/cloud-platform" });
            }
            var tokenAccess = (Google.Apis.Auth.OAuth2.ITokenAccess)credential;
            config.SaslPassword = tokenAccess.GetAccessTokenForRequestAsync().GetAwaiter().GetResult();
        }
        else
        {
            // Static SCRAM / Plain creds (e.g. local dev server with SASL_PLAINTEXT + SCRAM-SHA-256).
            config.SaslUsername = options.SaslUsername;
            config.SaslPassword = options.SaslPassword;
        }
    }

    public static void AttachOAuth<TKey, TValue>(ProducerBuilder<TKey, TValue> builder, KafkaOptions options)
    {
        if (options.SaslMechanism.Equals("OAuthBearer", StringComparison.OrdinalIgnoreCase))
        {
            builder.SetOAuthBearerTokenRefreshHandler(OauthTokenRefreshCallback);
        }
    }

    public static void AttachOAuth<TKey, TValue>(ConsumerBuilder<TKey, TValue> builder, KafkaOptions options)
    {
        if (options.SaslMechanism.Equals("OAuthBearer", StringComparison.OrdinalIgnoreCase))
        {
            builder.SetOAuthBearerTokenRefreshHandler(OauthTokenRefreshCallback);
        }
    }

    private static void OauthTokenRefreshCallback(IClient client, string config)
    {
        try
        {
            var credential = Google.Apis.Auth.OAuth2.GoogleCredential.GetApplicationDefaultAsync().GetAwaiter().GetResult();
            if (credential.IsCreateScopedRequired)
            {
                credential = credential.CreateScoped(new[] { "https://www.googleapis.com/auth/cloud-platform" });
            }
            var tokenAccess = (Google.Apis.Auth.OAuth2.ITokenAccess)credential;
            var token = tokenAccess.GetAccessTokenForRequestAsync().GetAwaiter().GetResult();
            long lifetimeMs = new DateTimeOffset(DateTime.UtcNow.AddMinutes(50)).ToUnixTimeMilliseconds();
            var principal = Environment.GetEnvironmentVariable("WorkerSaEmail") ?? "som-worker";
            client.OAuthBearerSetToken(token, lifetimeMs, principal);
        }
        catch (Exception ex)
        {
            client.OAuthBearerSetTokenFailure(ex.ToString());
        }
    }
}
