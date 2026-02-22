import {CollisionInfo, DiagnosticEntry, ReferenceEntry} from "./types.js";
import {
    getChangedFilesList,
    getMode,
    getSingleSourceFile,
    getSourceFile,
    optionalString,
    requireProject,
    requireString,
    setMode,
    setProject,
    setSingleSourceFile,
    snapshotSources,
} from "./state.js";
import {
    addDeclarationToTarget,
    buildSkeletonForFile,
    diagnosticSeverity,
    findNamedDeclaration,
    findRenameableIdentifiers,
    findSymbolIdentifier,
    removeDeclaration,
    updateImportsForMove,
} from "./ast.js";
import {Node, Project, ts} from "ts-morph";
import {originalSources, VIRTUAL_FILE} from "./constants.js";

export function handleInit(params: Record<string, unknown>): { ok: true } {
    const source = requireString(params, "source");
    const p = new Project({useInMemoryFileSystem: true});
    setProject(p);
    setSingleSourceFile(p.createSourceFile(VIRTUAL_FILE, source));
    setMode("single");
    originalSources.clear();
    return {ok: true};
}

export function handleInitProject(
    params: Record<string, unknown>,
): { ok: true; files: string[] } {
    const rootDir = requireString(params, "root_dir");
    const tsconfigPath = optionalString(params, "tsconfig_path");

    if (tsconfigPath) {
        setProject(new Project({tsConfigFilePath: tsconfigPath}));
    } else {
        const p = new Project({
            compilerOptions: {
                target: ts.ScriptTarget.ES2022,
                module: ts.ModuleKind.Node16,
                moduleResolution: ts.ModuleResolutionKind.Node16,
                strict: true,
                esModuleInterop: true,
            },
        });
        p.addSourceFilesAtPaths(`${rootDir}/**/*.{ts,tsx}`);
        setProject(p);
    }

    setMode("project");
    setSingleSourceFile(null);
    snapshotSources();

    const files = requireProject()
        .getSourceFiles()
        .map((sf) => sf.getFilePath());
    return {ok: true, files};
}

export function handleGetSkeleton(params: Record<string, unknown>): string {
    const sf = getSourceFile(params);
    return buildSkeletonForFile(sf);
}

export function handleRenameSymbol(params: Record<string, unknown>): object {
    const p = requireProject();
    const oldName = requireString(params, "old_name");
    const newName = requireString(params, "new_name");
    const scopeNode = optionalString(params, "scope_node");
    const sf = getSourceFile(params);

    const identifiers = findRenameableIdentifiers(sf, oldName, scopeNode);
    if (identifiers.length === 0) {
        return {summary: `ERROR: symbol '${oldName}' not found in file`};
    }

    const renamedLines = identifiers.map((id) => id.getStartLineNumber());
    renamedLines.sort((a, b) => a - b);

    const first = identifiers[0]!;
    first.rename(newName);

    const scopeNote = scopeNode
        ? ` within scope '${scopeNode}'`
        : " (file-wide)";
    const summary =
        `Renamed '${oldName}' → '${newName}'${scopeNote}: ` +
        `${renamedLines.length} occurrence(s) at ` +
        `lines [${renamedLines.join(", ")}]`;

    const changedFiles = getChangedFilesList(p);
    return {summary, changed_files: changedFiles};
}

export function handleFindReferences(
    params: Record<string, unknown>,
): ReferenceEntry[] {
    const sf = getSourceFile(params);
    const symbolName = requireString(params, "symbol_name");

    const identifier = findSymbolIdentifier(sf, symbolName);
    if (!identifier) {
        throw new Error(`Symbol '${symbolName}' not found in file`);
    }

    const referencedSymbols = identifier.findReferences();
    const entries: ReferenceEntry[] = [];

    for (const refSymbol of referencedSymbols) {
        const def = refSymbol.getDefinition();
        entries.push({
            file: def.getSourceFile().getFilePath(),
            line: def.getTextSpan().getStart(),
            column: 0,
            text: def.getNode().getText().slice(0, 80),
            is_definition: true,
        });
        for (const ref of refSymbol.getReferences()) {
            const refSf = ref.getSourceFile();
            const node = ref.getNode();
            entries.push({
                file: refSf.getFilePath(),
                line: node.getStartLineNumber(),
                column: node.getStart() - node.getStartLinePos(),
                text: node.getText().slice(0, 80),
                is_definition: ref.isDefinition() ?? false,
            });
        }
    }
    return entries;
}

export function handleGetSource(params: Record<string, unknown>): string {
    const sf = getSourceFile(params);
    return sf.getFullText();
}

export function handleGetChangedFiles(): { files: string[] } {
    const p = requireProject();
    return {files: getChangedFilesList(p)};
}

export function handleRemoveNode(params: Record<string, unknown>): object {
    const sf = getSourceFile(params);
    const symbolName = requireString(params, "symbol_name");
    const kind = optionalString(params, "kind");

    const decl = findNamedDeclaration(sf, symbolName, kind);
    if (!decl) {
        throw new Error(
            `Declaration '${symbolName}' not found` +
            (kind ? ` (kind: ${kind})` : ""),
        );
    }

    const line = decl.getStartLineNumber();
    const nodeKind = decl.getKindName();

    if (Node.isVariableDeclaration(decl)) {
        const declList = decl.getParent();
        if (
            Node.isVariableDeclarationList(declList) &&
            declList.getDeclarations().length === 1
        ) {
            const stmt = declList.getParent();
            if (Node.isVariableStatement(stmt)) {
                stmt.remove();
            } else {
                decl.remove();
            }
        } else {
            decl.remove();
        }
    } else {
        (decl as unknown as { remove(): void }).remove();
    }

    const p = requireProject();
    return {
        summary: `Removed ${nodeKind} '${symbolName}' (was at line ${line})`,
        changed_files: getChangedFilesList(p),
    };
}

export function handleMoveSymbolToFile(params: Record<string, unknown>): object {
    const p = requireProject();
    const sourceFilePath = requireString(params, "source_file");
    const targetFilePath = requireString(params, "target_file");
    const symbolName = requireString(params, "symbol_name");

    const sourceSf = p.getSourceFile(sourceFilePath);
    if (!sourceSf) {
        throw new Error(`Source file not found: ${sourceFilePath}`);
    }

    let targetSf = p.getSourceFile(targetFilePath);
    if (!targetSf) {
        targetSf = p.createSourceFile(targetFilePath, "");
    }

    const decl = findNamedDeclaration(sourceSf, symbolName);
    if (!decl) {
        throw new Error(
            `Declaration '${symbolName}' not found in ${sourceFilePath}`,
        );
    }

    addDeclarationToTarget(decl, targetSf);
    updateImportsForMove(p, sourceSf, targetSf, symbolName);
    removeDeclaration(decl);

    try {
        targetSf.fixMissingImports();
    } catch {
        // fixMissingImports can fail in some configurations
    }

    return {
        summary:
            `Moved '${symbolName}' from ` +
            `${sourceFilePath} to ${targetFilePath}`,
        changed_files: getChangedFilesList(p),
    };
}

export function handleOrganizeImports(params: Record<string, unknown>): object {
    const sf = getSourceFile(params);
    sf.organizeImports();
    const p = requireProject();
    return {
        summary: `Organized imports in ${sf.getFilePath()}`,
        changed_files: getChangedFilesList(p),
    };
}

export function handleFormatFile(params: Record<string, unknown>): object {
    const sf = getSourceFile(params);
    sf.formatText();
    const p = requireProject();
    return {
        summary: `Formatted ${sf.getFilePath()}`,
        changed_files: getChangedFilesList(p),
    };
}

export function handleGetDiagnostics(
    params: Record<string, unknown>,
): DiagnosticEntry[] {
    const p = requireProject();
    const filePath = optionalString(params, "file_path");

    const rawDiags = filePath
        ? p
            .getPreEmitDiagnostics()
            .filter(
                (d) => d.getSourceFile()?.getFilePath() === filePath,
            )
        : p.getPreEmitDiagnostics();

    return rawDiags.map((d) => {
        const raw = d.getMessageText();
        const msg =
            typeof raw === "string"
                ? raw
                : ts.flattenDiagnosticMessageText(raw.compilerObject, "\n");
        return {
            file: d.getSourceFile()?.getFilePath() ?? "<unknown>",
            line: d.getLineNumber() ?? 0,
            column: 0,
            message: msg,
            severity: diagnosticSeverity(d.getCategory()),
            code: d.getCode(),
        };
    });
}

export function handleCheckNameCollisions(
    params: Record<string, unknown>,
): CollisionInfo[] {
    const sf = getSourceFile(params);
    const newName = requireString(params, "new_name");
    const collisions: CollisionInfo[] = [];

    for (const fn of sf.getFunctions()) {
        if (fn.getName() === newName) {
            collisions.push({
                location: `line ${fn.getStartLineNumber()}`,
                kind: "FunctionDef",
            });
        }
    }
    for (const cls of sf.getClasses()) {
        if (cls.getName() === newName) {
            collisions.push({
                location: `line ${cls.getStartLineNumber()}`,
                kind: "ClassDef",
            });
        }
    }
    for (const vs of sf.getVariableStatements()) {
        for (const decl of vs.getDeclarations()) {
            if (decl.getName() === newName) {
                collisions.push({
                    location: `line ${decl.getStartLineNumber()}`,
                    kind: "VariableDeclaration",
                });
            }
        }
    }
    return collisions;
}

export function handleToSource(): string {
    if (getMode() === "single") {
        const sf = getSingleSourceFile();
        if (!sf) {
            throw new Error("No source file loaded (call init first)");
        }
        return sf.getFullText();
    }
    throw new Error("to_source is for single-file mode; use get_source instead");
}

export function handleExtractFunction(): string {
    return (
        "ERROR: extract_function is not yet implemented for TypeScript; " +
        "use rename_symbol, remove_node, and move_symbol_to_file instead."
    );
}