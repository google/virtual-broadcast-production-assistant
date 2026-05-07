/**
 * SOM Skill Worker — Node/TypeScript starter.
 *
 * Consumes story.context from Kafka, evaluates every registered skill's rules
 * via the rule engine, and publishes matches to som.skills.staging + audit
 * records to som.skills.runs.
 *
 * To add or change skills, drop a JSON file into skills/ — no code changes needed.
 */

import { Kafka } from "kafkajs";
import { buildKafkaConfig, GROUP_ID, TOPICS } from "./config.js";
import { SkillRegistry } from "./skill-registry.js";
import { evaluate } from "./rule-engine.js";
import { buildWarning, buildRunRecord } from "./message-builders.js";

export async function startWorker(): Promise<void> {
  const registry = new SkillRegistry();
  const skills = registry.all();

  if (skills.length === 0) {
    console.warn("No skills loaded — check your skills/ directory");
  }

  const kafka = new Kafka(buildKafkaConfig("som-skill-worker"));
  const consumer = kafka.consumer({ groupId: GROUP_ID });
  const producer = kafka.producer({ idempotent: true });

  await producer.connect();
  await consumer.connect();
  await consumer.subscribe({ topic: TOPICS.storyContext, fromBeginning: false });

  console.log(
    `SkillWorker subscribed to ${TOPICS.storyContext} with ${skills.length} skill(s) loaded`
  );

  await consumer.run({
    eachMessage: async ({ message }) => {
      try {
        if (!message.value) return;

        const envelope = JSON.parse(message.value.toString());
        // SOM v0.2 envelope wraps the story under "payload"; tolerate flat payloads too.
        const storyContext = envelope.payload ?? envelope;
        const storyId: string = storyContext.story_id ?? "unknown";
        const messageKey = message.key?.toString();

        console.log(`Received story ${storyId}`);

        // Run every registered skill against this story.
        for (const skill of registry.all()) {
          await evaluateSkill(producer, skill, storyContext, storyId, messageKey);
        }
      } catch (err) {
        console.error("Skill execution error:", err);
      }
    },
  });
}

async function evaluateSkill(
  producer: any,
  skill: any,
  storyContext: any,
  storyId: string,
  messageKey: string | undefined
): Promise<void> {
  const startMs = performance.now();
  const warningIds: string[] = [];

  for (const rule of skill.rules) {
    const matches = evaluate(rule, storyContext);
    for (const match of matches) {
      const warning = buildWarning(skill, match, storyId);
      warningIds.push(warning.warning_id);
      await producer.send({
        topic: TOPICS.skillsStaging,
        messages: [{ key: storyId, value: JSON.stringify(warning) }],
      });
    }
  }

  const latencyMs = Math.round(performance.now() - startMs);

  const runRecord = buildRunRecord(
    skill,
    storyId,
    messageKey,
    warningIds,
    [],
    [],
    latencyMs
  );

  await producer.send({
    topic: TOPICS.skillsRuns,
    messages: [{ key: storyId, value: JSON.stringify(runRecord) }],
  });

  console.log(
    `Skill ${skill.id}@${skill.version} on ${storyId}: ${warningIds.length} warnings in ${latencyMs}ms`
  );
}
