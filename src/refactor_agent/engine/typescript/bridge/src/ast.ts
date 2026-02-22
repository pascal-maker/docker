import {
    type Identifier,
    Node,
    Project,
    SourceFile,
    StructureKind,
    ts,
} from "ts-morph";

export function findNamedDeclaration(
    sf: SourceFile,
    name: string,
    kind: string | null = null,
): Node | null {
    if (!kind || kind === "function") {
        const fn = sf.getFunction(name);
        if (fn) return fn;
    }
    if (!kind || kind === "class") {
        const cls = sf.getClass(name);
        if (cls) return cls;
    }
    if (!kind || kind === "interface") {
        const iface = sf.getInterface(name);
        if (iface) return iface;
    }
    if (!kind || kind === "type_alias") {
        const ta = sf.getTypeAlias(name);
        if (ta) return ta;
    }
    if (!kind || kind === "enum") {
        const e = sf.getEnum(name);
        if (e) return e;
    }
    if (!kind || kind === "variable") {
        const v = sf.getVariableDeclaration(name);
        if (v) return v;
    }
    return null;
}

export function findRenameableIdentifiers(
    sf: SourceFile,
    name: string,
    scopeNode: string | null,
): Identifier[] {
    const searchRoot: Node = scopeNode ? findScope(sf, scopeNode) ?? sf : sf;
    const declarations: Identifier[] = [];
    const usages: Identifier[] = [];

    searchRoot.forEachDescendant((node) => {
        if (!Node.isIdentifier(node)) return;
        if (node.getText() !== name) return;
        const parent = node.getParent();
        if (!parent) return;

        const isDecl =
            Node.isFunctionDeclaration(parent) ||
            Node.isClassDeclaration(parent) ||
            Node.isInterfaceDeclaration(parent) ||
            Node.isTypeAliasDeclaration(parent) ||
            Node.isEnumDeclaration(parent) ||
            Node.isVariableDeclaration(parent) ||
            Node.isParameterDeclaration(parent) ||
            Node.isPropertyDeclaration(parent) ||
            Node.isPropertySignature(parent) ||
            Node.isMethodDeclaration(parent) ||
            Node.isMethodSignature(parent) ||
            Node.isImportSpecifier(parent) ||
            Node.isExportSpecifier(parent);

        if (isDecl) {
            declarations.push(node);
        } else {
            usages.push(node);
        }
    });

    if (declarations.length > 0) return declarations.slice(0, 1);
    return usages.slice(0, 1);
}

function findScope(sf: SourceFile, name: string): Node | null {
    for (const fn of sf.getFunctions()) {
        if (fn.getName() === name) return fn;
    }
    for (const cls of sf.getClasses()) {
        if (cls.getName() === name) return cls;
    }
    return null;
}

/**
 * Find the first identifier for a named symbol in a source file,
 * preferring declarations over usages.
 */
export function findSymbolIdentifier(
    sf: SourceFile,
    name: string,
): Identifier | null {
    const ids = findRenameableIdentifiers(sf, name, null);
    return ids[0] ?? null;
}

export function buildSkeletonForFile(sf: SourceFile): string {
    const parts: string[] = [];

    for (const fn of sf.getFunctions()) {
        const line = fn.getStartLineNumber();
        const args = fn.getParameters().map((p) => p.getName());
        const calls = new Set<string>();
        const assigns = new Set<string>();
        fn.forEachDescendant((node) => {
            if (Node.isCallExpression(node)) {
                const expr = node.getExpression();
                if (Node.isIdentifier(expr)) calls.add(expr.getText());
            }
            if (Node.isVariableDeclaration(node)) assigns.add(node.getName());
        });
        const lines = [
            `FunctionDef '${fn.getName() ?? "(anonymous)"}' (line ${line})`,
        ];
        if (args.length > 0) lines.push(`  args: ${args.join(", ")}`);
        if (calls.size > 0) {
            lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
        }
        if (assigns.size > 0) {
            lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
        }
        parts.push(lines.join("\n"));
    }

    for (const cls of sf.getClasses()) {
        const line = cls.getStartLineNumber();
        const calls = new Set<string>();
        const assigns = new Set<string>();
        cls.forEachDescendant((node) => {
            if (Node.isCallExpression(node)) {
                const expr = node.getExpression();
                if (Node.isIdentifier(expr)) calls.add(expr.getText());
            }
            if (Node.isVariableDeclaration(node)) assigns.add(node.getName());
        });
        const lines = [
            `ClassDef '${cls.getName() ?? "(anonymous)"}' (line ${line})`,
        ];
        if (calls.size > 0) {
            lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
        }
        if (assigns.size > 0) {
            lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
        }
        parts.push(lines.join("\n"));
    }

    return parts.join("\n\n");
}

/**
 * Strip the named import of `symbolName` from any import in `sf`
 * that resolves to `fromSf`. Removes the entire import declaration
 * when no specifiers remain.
 */
export function stripNamedImport(
    sf: SourceFile,
    fromSf: SourceFile,
    symbolName: string,
): void {
    for (const imp of sf.getImportDeclarations()) {
        if (imp.getModuleSpecifierSourceFile() !== fromSf) continue;
        const named = imp
            .getNamedImports()
            .find((ni) => ni.getName() === symbolName);
        if (!named) continue;

        named.remove();
        if (
            imp.getNamedImports().length === 0 &&
            !imp.getDefaultImport()
        ) {
            imp.remove();
        }
    }
}

export function addDeclarationToTarget(
    decl: Node,
    targetSf: SourceFile,
): void {
    if (Node.isFunctionDeclaration(decl)) {
        const s = decl.getStructure();
        if (s.kind === StructureKind.Function) {
            s.isExported = true;
            targetSf.addFunction(s);
        }
    } else if (Node.isClassDeclaration(decl)) {
        const s = decl.getStructure();
        s.isExported = true;
        targetSf.addClass(s);
    } else if (Node.isInterfaceDeclaration(decl)) {
        const s = decl.getStructure();
        s.isExported = true;
        targetSf.addInterface(s);
    } else if (Node.isTypeAliasDeclaration(decl)) {
        const s = decl.getStructure();
        s.isExported = true;
        targetSf.addTypeAlias(s);
    } else if (Node.isEnumDeclaration(decl)) {
        const s = decl.getStructure();
        s.isExported = true;
        targetSf.addEnum(s);
    } else if (Node.isVariableDeclaration(decl)) {
        const declList = decl.getParent();
        if (!Node.isVariableDeclarationList(declList)) {
            throw new Error("Cannot determine variable statement");
        }
        const stmt = declList.getParent();
        if (!Node.isVariableStatement(stmt)) {
            throw new Error("Cannot determine variable statement");
        }
        const s = stmt.getStructure();
        s.isExported = true;
        targetSf.addVariableStatement(s);
    } else {
        throw new Error(
            `Unsupported declaration kind for move: ${decl.getKindName()}`,
        );
    }
}

export function removeDeclaration(decl: Node): void {
    if (Node.isVariableDeclaration(decl)) {
        const declList = decl.getParent();
        if (
            Node.isVariableDeclarationList(declList) &&
            declList.getDeclarations().length === 1
        ) {
            const stmt = declList.getParent();
            if (Node.isVariableStatement(stmt)) {
                stmt.remove();
                return;
            }
        }
        decl.remove();
    } else {
        (decl as unknown as { remove(): void }).remove();
    }
}

export function diagnosticSeverity(category: ts.DiagnosticCategory): string {
    switch (category) {
        case ts.DiagnosticCategory.Error:
            return "error";
        case ts.DiagnosticCategory.Warning:
            return "warning";
        case ts.DiagnosticCategory.Suggestion:
            return "suggestion";
        case ts.DiagnosticCategory.Message:
            return "message";
        default:
            return "unknown";
    }
}

export function updateImportsForMove(
    p: Project,
    sourceSf: SourceFile,
    targetSf: SourceFile,
    symbolName: string,
): void {
    // Target already has the declaration locally; drop its old import.
    stripNamedImport(targetSf, sourceSf, symbolName);

    for (const sf of p.getSourceFiles()) {
        if (sf === sourceSf || sf === targetSf) continue;

        const imp = sf
            .getImportDeclarations()
            .find(
                (i) =>
                    i.getModuleSpecifierSourceFile() === sourceSf &&
                    i.getNamedImports().some((ni) => ni.getName() === symbolName),
            );
        if (!imp) continue;

        stripNamedImport(sf, sourceSf, symbolName);

        const existing = sf
            .getImportDeclarations()
            .find(
                (i) => i.getModuleSpecifierSourceFile() === targetSf,
            );
        if (existing) {
            existing.addNamedImport(symbolName);
        } else {
            const specifier =
                sf.getRelativePathAsModuleSpecifierTo(targetSf);
            sf.addImportDeclaration({
                namedImports: [symbolName],
                moduleSpecifier: specifier,
            });
        }
    }
}