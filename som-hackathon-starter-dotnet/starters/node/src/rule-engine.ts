/**
 * Generic rule interpreter — matches the .NET RuleEngine exactly.
 *
 * Supported rule types:
 *   term_match               — fires once per matching term in a field
 *   phase_with_missing_field — fires when phase matches AND a field is null/empty
 *   field_value_in           — fires when a field matches one of a set of values
 *   field_present            — fires when a field exists and is not null/empty
 *   field_absent             — fires when a field is missing or null/empty
 *   field_regex              — fires when a field matches a regex pattern
 */

import type { SkillRule } from "./skill-registry.js";

export interface RuleMatch {
  rule: SkillRule;
  detail: string;
}

export function evaluate(rule: SkillRule, story: any): RuleMatch[] {
  switch (rule.type) {
    case "term_match":
      return evalTermMatch(rule, story);
    case "phase_with_missing_field":
      return evalPhaseMissingField(rule, story);
    case "field_value_in":
      return evalFieldValueIn(rule, story);
    case "field_present":
      return evalFieldPresent(rule, story, true);
    case "field_absent":
      return evalFieldPresent(rule, story, false);
    case "field_regex":
      return evalFieldRegex(rule, story);
    default:
      return [];
  }
}

// ── Rule type implementations ───────────────────────────────────

function evalTermMatch(rule: SkillRule, story: any): RuleMatch[] {
  const field = rule.config.field as string | undefined;
  const terms = (rule.config.terms ?? []) as string[];
  const caseSensitive = (rule.config.case_sensitive ?? false) as boolean;
  if (!field || terms.length === 0) return [];

  const value = getByPath(story, field);
  if (typeof value !== "string" || !value) return [];

  const haystack = caseSensitive ? value : value.toLowerCase();
  const matches: RuleMatch[] = [];

  for (const term of terms) {
    const needle = caseSensitive ? term : term.toLowerCase();
    if (haystack.includes(needle)) {
      matches.push({
        rule,
        detail: renderDetail(rule, { term, field, value }),
      });
    }
  }
  return matches;
}

function evalPhaseMissingField(rule: SkillRule, story: any): RuleMatch[] {
  const phaseField = (rule.config.phase_field ?? "lifecycle.phase") as string;
  const phase = rule.config.phase as string | undefined;
  const field = rule.config.field as string | undefined;
  if (!phase || !field) return [];

  const actualPhase = getByPath(story, phaseField);
  if (typeof actualPhase !== "string") return [];
  if (actualPhase.toLowerCase() !== phase.toLowerCase()) return [];

  if (isEmpty(getByPath(story, field))) {
    return [{ rule, detail: renderDetail(rule, { phase, field }) }];
  }
  return [];
}

function evalFieldValueIn(rule: SkillRule, story: any): RuleMatch[] {
  const field = rule.config.field as string | undefined;
  const values = (rule.config.values ?? []) as string[];
  if (!field || values.length === 0) return [];

  const actual = getByPath(story, field);
  if (typeof actual !== "string") return [];

  for (const v of values) {
    if (actual.toLowerCase() === v.toLowerCase()) {
      return [{ rule, detail: renderDetail(rule, { value: v, field }) }];
    }
  }
  return [];
}

function evalFieldPresent(
  rule: SkillRule,
  story: any,
  expectPresent: boolean
): RuleMatch[] {
  const field = rule.config.field as string | undefined;
  if (!field) return [];

  const present = !isEmpty(getByPath(story, field));
  if (present === expectPresent) {
    return [{ rule, detail: renderDetail(rule, { field }) }];
  }
  return [];
}

function evalFieldRegex(rule: SkillRule, story: any): RuleMatch[] {
  const field = rule.config.field as string | undefined;
  const pattern = rule.config.pattern as string | undefined;
  const caseSensitive = (rule.config.case_sensitive ?? false) as boolean;
  if (!field || !pattern) return [];

  const value = getByPath(story, field);
  if (typeof value !== "string") return [];

  let re: RegExp;
  try {
    re = new RegExp(pattern, caseSensitive ? "" : "i");
  } catch {
    return [];
  }

  const m = re.exec(value);
  if (m) {
    return [
      {
        rule,
        detail: renderDetail(rule, { match: m[0], field, value }),
      },
    ];
  }
  return [];
}

// ── Helpers ─────────────────────────────────────────────────────

/** Walk a dotted path, e.g. "lifecycle.phase" → story.lifecycle.phase */
export function getByPath(obj: any, path: string): any {
  let current = obj;
  for (const part of path.split(".")) {
    if (current == null || typeof current !== "object") return undefined;
    current = current[part];
  }
  return current;
}

function isEmpty(value: any): boolean {
  if (value == null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "string") return value.trim() === "";
  return false;
}

function renderDetail(
  rule: SkillRule,
  subs: Record<string, string>
): string {
  let template = rule.detail_template || rule.description || rule.name;
  for (const [k, v] of Object.entries(subs)) {
    template = template.replaceAll(`{${k}}`, v);
  }
  return template;
}
