/**
 * SOM Skill Worker — Node/TypeScript starter
 *
 * Entry point. Runs in one of two modes:
 *   --test-producer [--story <name>]  → publishes seed stories to Kafka
 *   (default)                          → starts the skill worker consumer loop
 */

import { runTestProducer } from "./test-producer.js";
import { startWorker } from "./skill-worker.js";

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.includes("--test-producer")) {
    const storyIdx = args.indexOf("--story");
    const scenario =
      storyIdx >= 0 && storyIdx + 1 < args.length
        ? args[storyIdx + 1]
        : undefined;
    await runTestProducer(scenario);
    return;
  }

  // Default: run the skill worker
  await startWorker();
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
