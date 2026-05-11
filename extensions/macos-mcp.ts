import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type ToolResult = {
  content?: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
  [key: string]: unknown;
};

function resultToText(result: ToolResult): string {
  const parts = (result.content ?? [])
    .map((item) => {
      if (item.type === "text") return item.text ?? "";
      if (item.type === "image") return `[image omitted: ${item.mimeType ?? "image"}]`;
      return JSON.stringify(item);
    })
    .filter(Boolean);
  return parts.length ? parts.join("\n") : JSON.stringify(result, null, 2);
}

function isMacosMcpRoot(path: string): boolean {
  return existsSync(resolve(path, "src/macos_mcp/__main__.py")) &&
    existsSync(resolve(path, "pyproject.toml"));
}

function findProjectRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  const candidates = [
    process.env.MACOS_MCP_ROOT,
    process.cwd(),
    resolve(process.cwd(), "MacOS-MCP"),
    resolve(here, ".."),
    resolve(here, "../.."),
    resolve(here, "../../.."),
  ].filter((path): path is string => Boolean(path));

  const root = candidates.find(isMacosMcpRoot);
  if (!root) {
    throw new Error(
      "Could not find the macOS-MCP project root. Run Pi from the MacOS-MCP checkout, " +
      "install this package via `pi install git:github.com/CursorTouch/MacOS-MCP`, " +
      "or set MACOS_MCP_ROOT=/path/to/MacOS-MCP."
    );
  }
  return root;
}

export default function (pi: ExtensionAPI) {
  let client: Client | undefined;
  let connecting: Promise<Client> | undefined;

  async function getClient(): Promise<Client> {
    if (client) return client;
    if (!connecting) {
      connecting = (async () => {
        const transport = new StdioClientTransport({
          command: "uv",
          args: ["run", "macos-mcp"],
          cwd: findProjectRoot(),
        });
        const next = new Client({ name: "pi-macos-mcp", version: "0.1.0" });
        try {
          await next.connect(transport);
          client = next;
          return next;
        } catch (error) {
          connecting = undefined;
          try { await next.close(); } catch {}
          throw error;
        }
      })();
    }
    return connecting;
  }

  async function callMac(tool: string, args: Record<string, unknown>) {
    const activeClient = await getClient();
    const result = (await activeClient.callTool({ name: tool, arguments: args })) as ToolResult;
    return { content: [{ type: "text" as const, text: resultToText(result) }], details: result };
  }

  pi.on("session_shutdown", async () => {
    try { await client?.close(); } catch {}
    client = undefined;
    connecting = undefined;
  });

  pi.registerTool({
    name: "mac_snapshot",
    label: "macOS Snapshot",
    description: "Read macOS UI state through macOS-MCP Snapshot. Returns interactive elements and coordinates; set use_vision=true only when an annotated screenshot is needed.",
    promptSnippet: "Inspect macOS UI state through macOS-MCP.",
    promptGuidelines: [
      "Use mac_snapshot before controlling macOS applications with macOS-MCP tools.",
      "Prefer the coordinates returned by mac_snapshot for mac_click and mac_type.",
      "Use use_vision=true only when Accessibility data is missing or ambiguous.",
    ],
    parameters: Type.Object({
      use_vision: Type.Optional(Type.Boolean({ default: false })),
    }),
    async execute(_id, params) {
      return callMac("Snapshot", { use_vision: params.use_vision ?? false });
    },
  });

  pi.registerTool({
    name: "mac_app",
    label: "macOS App",
    description: "Launch, switch, move, or resize macOS applications/windows through macOS-MCP.",
    parameters: Type.Object({
      mode: Type.Union([Type.Literal("launch"), Type.Literal("switch"), Type.Literal("resize")]),
      name: Type.Optional(Type.String()),
      window_loc: Type.Optional(Type.Array(Type.Number(), { minItems: 2, maxItems: 2 })),
      window_size: Type.Optional(Type.Array(Type.Number(), { minItems: 2, maxItems: 2 })),
    }),
    async execute(_id, params) {
      return callMac("App", params as Record<string, unknown>);
    },
  });

  pi.registerTool({
    name: "mac_click",
    label: "macOS Click",
    description: "Click macOS screen coordinates through macOS-MCP. Get coordinates from mac_snapshot first.",
    parameters: Type.Object({
      loc: Type.Array(Type.Number(), { minItems: 2, maxItems: 2, description: "Screen coordinates [x, y]." }),
      button: Type.Optional(Type.Union([Type.Literal("left"), Type.Literal("right"), Type.Literal("middle")], { default: "left" })),
      clicks: Type.Optional(Type.Number({ default: 1, description: "0=hover, 1=single click, 2=double click." })),
    }),
    async execute(_id, params) {
      return callMac("Click", {
        loc: params.loc,
        button: params.button ?? "left",
        clicks: params.clicks ?? 1,
      });
    },
  });

  pi.registerTool({
    name: "mac_type",
    label: "macOS Type",
    description: "Type text at macOS screen coordinates through macOS-MCP. Get coordinates from mac_snapshot first.",
    parameters: Type.Object({
      loc: Type.Array(Type.Number(), { minItems: 2, maxItems: 2, description: "Screen coordinates [x, y]." }),
      text: Type.String(),
      clear: Type.Optional(Type.Boolean({ default: false })),
      caret_position: Type.Optional(Type.Union([Type.Literal("start"), Type.Literal("idle"), Type.Literal("end")], { default: "idle" })),
      press_enter: Type.Optional(Type.Boolean({ default: false })),
    }),
    async execute(_id, params) {
      return callMac("Type", {
        loc: params.loc,
        text: params.text,
        clear: params.clear ?? false,
        caret_position: params.caret_position ?? "idle",
        press_enter: params.press_enter ?? false,
      });
    },
  });

  pi.registerTool({
    name: "mac_shortcut",
    label: "macOS Shortcut",
    description: "Run a macOS keyboard shortcut through macOS-MCP, e.g. command+c, command+l, command+space.",
    parameters: Type.Object({ shortcut: Type.String() }),
    async execute(_id, params) {
      return callMac("Shortcut", { shortcut: params.shortcut });
    },
  });

  pi.registerTool({
    name: "mac_scroll",
    label: "macOS Scroll",
    description: "Scroll vertically or horizontally through macOS-MCP. Coordinates are optional but recommended from mac_snapshot.",
    parameters: Type.Object({
      loc: Type.Optional(Type.Array(Type.Number(), { minItems: 2, maxItems: 2 })),
      type: Type.Optional(Type.Union([Type.Literal("horizontal"), Type.Literal("vertical")], { default: "vertical" })),
      direction: Type.Optional(Type.Union([Type.Literal("up"), Type.Literal("down"), Type.Literal("left"), Type.Literal("right")], { default: "down" })),
      wheel_times: Type.Optional(Type.Number({ default: 1 })),
    }),
    async execute(_id, params) {
      return callMac("Scroll", {
        loc: params.loc,
        type: params.type ?? "vertical",
        direction: params.direction ?? "down",
        wheel_times: params.wheel_times ?? 1,
      });
    },
  });

  pi.registerTool({
    name: "mac_wait",
    label: "macOS Wait",
    description: "Wait for UI loading/animations through macOS-MCP.",
    parameters: Type.Object({ duration: Type.Number({ description: "Seconds to wait." }) }),
    async execute(_id, params) {
      return callMac("Wait", { duration: params.duration });
    },
  });
}
