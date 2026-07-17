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

        if (options.SecurityProtocol.Equals("SaslSsl", StringComparison.OrdinalIgnoreCase))
        {
            if (options.SaslMechanism.Equals("Plain", StringComparison.OrdinalIgnoreCase))
            {
                config.SaslUsername = Environment.GetEnvironmentVariable("WorkerSaEmail") ?? options.SaslUsername;
                
                // Fetch short-lived access token as password
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
                config.SaslUsername = options.SaslUsername;
                config.SaslPassword = options.SaslPassword;
            }
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
