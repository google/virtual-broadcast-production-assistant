/**
 * Publishes seed story.context messages to som.story.context for local testing.
 *
 * Usage:
 *   npx tsx src/index.ts --test-producer                   → publishes all seed stories
 *   npx tsx src/index.ts --test-producer --story informal  → single scenario
 */

import { readFileSync, existsSync } from "fs";
import path from "path";
import { Kafka } from "kafkajs";
import { buildKafkaConfig, TOPICS } from "./config.js";

const SCENARIO_FILES: Record<string, string> = {
  breaking: "01-breaking-courthouse.json",
  election: "02-developing-election.json",
  informal: "03-informal-headline.json",
  clean: "04-clean-transit.json",
  "breaking-no-compliance": "05-breaking-no-compliance.json",
};

export const SCENARIOS = Object.keys(SCENARIO_FILES);

function resolveSeedPath(filename: string): string | null {
  // Try ../../seed-stories/ (relative to project root, shared with .NET)
  const candidates = [
    path.join(process.cwd(), "..", "..", "seed-stories", filename),
    path.join(__dirname, "..", "..", "..", "seed-stories", filename),
    path.join(process.cwd(), "seed-stories", filename),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return null;
}

export async function runTestProducer(scenario?: string): Promise<void> {
  const kafka = new Kafka(buildKafkaConfig("som-test-producer"));
  const producer = kafka.producer();
  await producer.connect();

  const scenarios = scenario ? [scenario] : Object.keys(SCENARIO_FILES);

  for (const name of scenarios) {
    const file = SCENARIO_FILES[name];
    if (!file) {
      console.log(
        `Unknown scenario '${name}'. Available: ${Object.keys(SCENARIO_FILES).join(", ")}`
      );
      continue;
    }

    const fullPath = resolveSeedPath(file);
    if (!fullPath) {
      console.log(`Seed file not found: ${file}`);
      continue;
    }

    const raw = readFileSync(fullPath, "utf-8");
    const envelope = JSON.parse(raw);
    const payload = envelope.payload;
    if (!payload) {
      console.log(`No payload in ${file}`);
      continue;
    }

    const storyId: string = payload.story_id ?? "unknown";

    console.log(`─── ${name.toUpperCase()} ───`);
    console.log(`  Story:    ${storyId}`);
    console.log(`  Headline: ${payload.headline}`);
    console.log(`  Phase:    ${payload.lifecycle?.phase}`);
    console.log(`  File:     ${file}`);

    const result = await producer.send({
      topic: TOPICS.storyContext,
      messages: [{ key: storyId, value: JSON.stringify(payload) }],
    });

    const record = result[0];
    console.log(
      `  → Partition ${record.partition}, Offset ${record.baseOffset}`
    );
    console.log();
  }

  await producer.disconnect();
  console.log("Done. Your skill worker should pick these up.");
}
