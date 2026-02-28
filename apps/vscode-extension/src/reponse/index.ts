// TODO: DEPRECATED
/** Parse "rename X to Y", "rename X Y", or JSON { old_name, new_name }. */
export function parseRenameIntentFromPrompt(
  prompt: string
): { old_name: string; new_name: string } | null {
  const trimmed = prompt.trim();
  try {
    const data = JSON.parse(trimmed) as {
      old_name?: string;
      new_name?: string;
    };
    if (
      typeof data?.old_name === "string" &&
      typeof data?.new_name === "string"
    ) {
      return { old_name: data.old_name, new_name: data.new_name };
    }
  } catch {
    // not JSON
  }
  const toMatch =
    trimmed.match(/rename\s+(\S+)\s+to\s+(\S+)/i) ||
    trimmed.match(/rename\s+(\S+)\s+(\S+)/i);
  if (toMatch) {
    return { old_name: toMatch[1], new_name: toMatch[2] };
  }
  return null;
}
