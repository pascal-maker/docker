export interface Request {
    id: number;
    method: string;
    params: Record<string, unknown>;
}

export interface CollisionInfo {
    location: string;
    kind: string;
}

export interface ReferenceEntry {
    file: string;
    line: number;
    column: number;
    text: string;
    is_definition: boolean;
}

export interface DiagnosticEntry {
    file: string;
    line: number;
    column: number;
    message: string;
    severity: string;
    code: number;
}

export type Mode = "idle" | "single" | "project";