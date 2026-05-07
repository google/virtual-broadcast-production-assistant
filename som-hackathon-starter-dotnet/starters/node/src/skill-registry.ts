/**
 * In-memory registry of skill definitions, backed by JSON files in skills/.
 * Loads all *.json files on startup.
 */

import { readdirSync, readFileSync } from "fs";
import path from "path";

export interface SkillRule {
  rule_id: string;
  name: string;
  description: string;
  type: string;
  config: Record<string, any>;
  default_severity: string;
  output_message_type: string;
  affected_fields: string[];
  detail_template?: string;
}

export interface SkillDefinition {
  id: string;
  version: string;
  name: string;
  description: string;
  skill_type: string;
  disclosure_level: string;
  migration_policy: string;
  reads: string[];
  produces: string[];
  rules: SkillRule[];
}

export class SkillRegistry {
  private skills = new Map<string, SkillDefinition>();

  constructor(skillsDir?: string) {
    const dir = skillsDir ?? this.resolveSkillsDir();
    this.loadAll(dir);
  }

  all(): SkillDefinition[] {
    return [...this.skills.values()];
  }

  get(id: string): SkillDefinition | undefined {
    return this.skills.get(id);
  }

  private loadAll(dir: string): void {
    let files: string[];
    try {
      files = readdirSync(dir).filter((f) => f.endsWith(".json"));
    } catch {
      console.warn(`Skills directory not found at ${dir} — starting empty`);
      return;
    }

    for (const file of files) {
      try {
        const raw = readFileSync(path.join(dir, file), "utf-8");
        const skill: SkillDefinition = JSON.parse(raw);
        this.skills.set(skill.id, skill);
        console.log(`Loaded skill ${skill.id}@${skill.version} from ${file}`);
      } catch (err) {
        console.error(`Failed to load skill from ${file}:`, err);
      }
    }
  }

  private resolveSkillsDir(): string {
    // Prefer skills/ relative to project root (where package.json lives)
    const candidates = [
      path.join(process.cwd(), "skills"),
      path.join(__dirname, "..", "skills"),
    ];
    for (const c of candidates) {
      try {
        readdirSync(c);
        return c;
      } catch {
        // next
      }
    }
    return candidates[0]; // fallback
  }
}
