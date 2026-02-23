import * as fs from "node:fs";
import * as path from "node:path";
import { Project, SourceFile } from "ts-morph";
import { originalSources } from "./constants.js";
import { Mode } from "./types.js";

let mode: Mode = "idle";
let project: Project | null = null;
let singleSourceFile: SourceFile | null = null;

export function setMode(m: Mode): void {
  mode = m;
}

export function setProject(p: Project | null): void {
  project = p;
}

export function setSingleSourceFile(sf: SourceFile | null): void {
  singleSourceFile = sf;
}

export function getMode(): Mode {
  return mode;
}

export function getSingleSourceFile(): SourceFile | null {
  return singleSourceFile;
}

export function requireString(
  params: Record<string, unknown>,
  key: string
): string {
  const v = params[key];
  if (typeof v !== "string") {
    throw new Error(`params.${key} must be a string`);
  }
  return v;
}

export function optionalString(
  params: Record<string, unknown>,
  key: string
): string | null {
  const v = params[key];
  if (v === undefined || v === null) return null;
  if (typeof v !== "string") {
    throw new Error(`params.${key} must be a string or null`);
  }
  return v;
}

export function requireProject(): Project {
  if (!project) {
    throw new Error("No project loaded (call init or init_project first)");
  }
  return project;
}

export function getSourceFile(params: Record<string, unknown>): SourceFile {
  if (mode === "single") {
    if (!singleSourceFile) {
      throw new Error("No source loaded (call init first)");
    }
    return singleSourceFile;
  }
  const filePath = requireString(params, "file_path");
  const p = requireProject();
  let sf = p.getSourceFile(filePath);
  if (!sf && path.isAbsolute(filePath)) {
    const normalized = path.normalize(filePath);
    for (const candidate of p.getSourceFiles()) {
      if (path.normalize(candidate.getFilePath()) === normalized) {
        sf = candidate;
        break;
      }
    }
    if (!sf) {
      let requestedReal: string;
      try {
        requestedReal = fs.realpathSync(filePath);
      } catch {
        requestedReal = "";
      }
      if (requestedReal) {
        for (const candidate of p.getSourceFiles()) {
          try {
            if (fs.realpathSync(candidate.getFilePath()) === requestedReal) {
              sf = candidate;
              break;
            }
          } catch {
            continue;
          }
        }
      }
    }
  }
  if (!sf) {
    throw new Error(`File not found in project: ${filePath}`);
  }
  return sf;
}

export function snapshotSources(): void {
  originalSources.clear();
  for (const sf of requireProject().getSourceFiles()) {
    originalSources.set(sf.getFilePath(), sf.getFullText());
  }
}

export function getChangedFilesList(p: Project): string[] {
  const changed: string[] = [];
  for (const sf of p.getSourceFiles()) {
    const fp = sf.getFilePath();
    const orig = originalSources.get(fp);
    if (orig === undefined || orig !== sf.getFullText()) {
      changed.push(fp);
    }
  }
  return changed;
}
