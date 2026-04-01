import { requireProject } from "./state.js";

const REACT_LIFECYCLE_METHODS = [
  "componentDidMount",
  "componentDidUpdate",
  "componentWillUnmount",
  "shouldComponentUpdate",
  "getSnapshotBeforeUpdate",
  "getDerivedStateFromProps",
  "componentDidCatch",
  "getDerivedStateFromError",
  "render",
] as const;

const REACT_BASE_CLASSES = new Set(["Component", "PureComponent"]);

interface ComponentEntry {
  file_path: string;
  component_name: string;
  lifecycle_methods: string[];
  has_state: boolean;
  has_refs: boolean;
  line: number;
}

export function handleListReactClassComponents(
  _params: Record<string, unknown>
): ComponentEntry[] {
  const p = requireProject();
  const entries: ComponentEntry[] = [];

  for (const sf of p.getSourceFiles()) {
    for (const cls of sf.getClasses()) {
      const baseExpr = cls.getExtends()?.getExpression();
      if (!baseExpr) continue;

      const baseText = baseExpr.getText();
      // Strip type arguments (e.g. "Component<Props, State>" → "Component")
      const baseTextRoot = baseText.replace(/<.*$/, "").trim();
      const baseName = cls.getBaseClass()?.getName() ?? "";

      const isReactClass =
        REACT_BASE_CLASSES.has(baseName) ||
        REACT_BASE_CLASSES.has(baseTextRoot) ||
        baseText === "React.Component" ||
        baseText.startsWith("React.Component<") ||
        baseText === "React.PureComponent" ||
        baseText.startsWith("React.PureComponent<");

      if (!isReactClass) continue;

      const lifecycleMethods = REACT_LIFECYCLE_METHODS.filter(
        (m) => cls.getMethod(m) !== undefined
      );

      const hasState = cls.getProperty("state") !== undefined;
      const hasRefs = cls
        .getProperties()
        .some(
          (prop) =>
            prop.getInitializer()?.getText().includes("createRef") ?? false
        );

      entries.push({
        file_path: sf.getFilePath(),
        component_name: cls.getName() ?? "<anonymous>",
        lifecycle_methods: [...lifecycleMethods],
        has_state: hasState,
        has_refs: hasRefs,
        line: cls.getStartLineNumber(),
      });
    }
  }
  return entries;
}
