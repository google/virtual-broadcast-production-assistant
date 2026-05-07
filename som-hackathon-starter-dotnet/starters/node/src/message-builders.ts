/**
 * SOM message builders — produces JSON shapes identical to the .NET SkillWorker.
 *
 * Field names, nesting, and types MUST match the .NET version exactly so the
 * shared dashboard can render outputs from any language starter.
 */

import { randomUUID } from "crypto";
import type { SkillDefinition } from "./skill-registry.js";
import type { RuleMatch } from "./rule-engine.js";

/** Build a skill.warning.raised message (hackathon brief §8.3). */
export function buildWarning(
  skill: SkillDefinition,
  match: RuleMatch,
  storyId: string
): Record<string, any> {
  const rule = match.rule;
  return {
    message_type: rule.output_message_type,
    warning_id: randomUUID(),
    skill_id: skill.id,
    skill_version: skill.version,
    story_id: storyId,
    severity: rule.default_severity,
    rule_id: rule.rule_id,
    non_overridable: false,
    affected_fields: [...rule.affected_fields],
    detail: match.detail,
    blocks: [],
    timestamp: new Date().toISOString(),
  };
}

/** Build a skill.suggestion.created message (Amendment 3). */
export function buildSuggestion(
  skill: SkillDefinition,
  storyId: string,
  contentType: string,
  variants: Record<string, any>[],
  instanceRef?: { instance_id: string; platform: string }
): Record<string, any> {
  return {
    message_type: "skill.suggestion.created",
    suggestion_id: randomUUID(),
    skill_id: skill.id,
    skill_version: skill.version,
    story_id: storyId,
    content_type: contentType,
    variants,
    human_review_required: true,
    timestamp: new Date().toISOString(),
    ...(instanceRef ? { instance_ref: instanceRef } : {}),
  };
}

/** Build a variant for use inside skill.suggestion.created. */
export function buildVariant(
  contentType: string,
  format: string,
  label: string,
  confidence: number,
  payload: any,
  previewText: string,
  assetRef?: string
): Record<string, any> {
  return {
    variant_id: randomUUID(),
    content_type: contentType,
    format,
    label,
    confidence,
    payload,
    preview: { text: previewText },
    ...(assetRef ? { asset_ref: assetRef } : {}),
  };
}

/** Build a story.enrichment message (Amendment 5). */
export function buildEnrichment(
  skill: SkillDefinition,
  storyId: string,
  representationType: string,
  language: string,
  content: string,
  contentKey: string
): Record<string, any> {
  return {
    message_type: "story.enrichment",
    enrichment_id: randomUUID(),
    skill_id: skill.id,
    skill_version: skill.version,
    story_id: storyId,
    representation_type: representationType,
    language,
    content,
    content_key: contentKey,
    timestamp: new Date().toISOString(),
  };
}

/** Build skill.run.completed audit record (Amendment 1, hackathon brief §8.1). */
export function buildRunRecord(
  skill: SkillDefinition,
  storyId: string,
  messageKey: string | undefined,
  warningIds: string[],
  suggestionIds: string[] = [],
  enrichmentIds: string[] = [],
  latencyMs: number
): Record<string, any> {
  return {
    message_type: "skill.run.completed",
    run_id: randomUUID(),
    skill_id: skill.id,
    skill_version: skill.version,
    story_id: storyId,
    triggered_by: {
      event_type: "story.context",
      message_id: messageKey ?? "",
    },
    inputs: {
      reads: [...skill.reads],
      input_digest: "", // TODO: sha256 of consumed fields
    },
    outputs: {
      suggestion_ids: suggestionIds,
      warning_ids: warningIds,
      enrichment_ids: enrichmentIds,
    },
    latency_ms: latencyMs,
    outcome: warningIds.length > 0 ? "COMPLETED" : "SKIPPED",
    human_review_required: warningIds.length > 0,
    timestamp: new Date().toISOString(),
  };
}
