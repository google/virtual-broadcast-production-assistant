/**
 * Kafka configuration — reads from env vars with sensible local-dev defaults.
 *
 * For Confluent Cloud: set KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET.
 */

import type { KafkaConfig, SASLOptions } from "kafkajs";

export const BOOTSTRAP_SERVERS =
  process.env.KAFKA_BOOTSTRAP_SERVERS ?? "localhost:9092";

// TODO: Change to your vendor's consumer group
export const GROUP_ID = process.env.KAFKA_GROUP_ID ?? "my-skill-group";

export const TOPICS = {
  storyContext: process.env.KAFKA_STORY_CONTEXT_TOPIC ?? "som.story.context",
  skillsStaging:
    process.env.KAFKA_SKILLS_STAGING_TOPIC ?? "som.skills.staging",
  skillsRuns: process.env.KAFKA_SKILLS_RUNS_TOPIC ?? "som.skills.runs",
} as const;

/** Build a KafkaJS client config, auto-detecting SaslSsl when creds are present. */
export function buildKafkaConfig(clientId: string): KafkaConfig {
  const config: KafkaConfig = {
    clientId,
    brokers: BOOTSTRAP_SERVERS.split(","),
  };

  const apiKey = process.env.KAFKA_API_KEY;
  const apiSecret = process.env.KAFKA_API_SECRET;

  if (apiKey && apiSecret) {
    const sasl: SASLOptions = {
      mechanism: "plain",
      username: apiKey,
      password: apiSecret,
    };
    config.ssl = true;
    config.sasl = sasl;
  }

  return config;
}
