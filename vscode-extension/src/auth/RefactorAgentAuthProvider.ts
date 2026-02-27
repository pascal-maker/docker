import * as vscode from "vscode";

const SESSION_SECRET_KEY = "refactor-agent.auth.session";
const DEFAULT_AUTH_SIGNIN_URL = "https://refactorum.com/auth/signin";
const GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code";
const GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token";
const GITHUB_DEVICE_URI = "https://github.com/login/device";

interface RefactorAgentSession extends vscode.AuthenticationSession {
  readonly accessToken: string;
  readonly account: { id: string; label: string };
  readonly id: string;
  readonly scopes: readonly string[];
}

interface DeviceCodeResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}

interface TokenResponse {
  access_token?: string;
  error?: string;
}

export class RefactorAgentAuthProvider
  implements vscode.AuthenticationProvider, vscode.Disposable
{
  static id = "refactor-agent.auth";
  private _onDidChangeSessions =
    new vscode.EventEmitter<vscode.AuthenticationProviderAuthenticationSessionsChangeEvent>();
  private _disposable: vscode.Disposable;
  private _pendingResolve:
    | ((session: RefactorAgentSession) => void)
    | undefined;
  private _pendingReject: ((err: Error) => void) | undefined;

  constructor(private readonly _context: vscode.ExtensionContext) {
    this._disposable = vscode.Disposable.from(
      vscode.authentication.registerAuthenticationProvider(
        RefactorAgentAuthProvider.id,
        "Refactor Agent",
        this,
        { supportsMultipleAccounts: false }
      )
    );
  }

  get onDidChangeSessions() {
    return this._onDidChangeSessions.event;
  }

  dispose(): void {
    this._disposable.dispose();
  }

  async getSessions(
    _scopes: readonly string[] | undefined
  ): Promise<RefactorAgentSession[]> {
    const token = await this._context.secrets.get(SESSION_SECRET_KEY);
    if (!token) return [];
    return [
      {
        id: RefactorAgentAuthProvider.id,
        accessToken: token,
        account: { id: RefactorAgentAuthProvider.id, label: "Refactor Agent" },
        scopes: [],
      },
    ];
  }

  async createSession(
    _scopes: readonly string[]
  ): Promise<RefactorAgentSession> {
    const choice = await vscode.window.showQuickPick(
      [
        {
          label: "Sign in with browser",
          description: "Opens GitHub in your browser (recommended)",
          value: "browser",
        },
        {
          label: "Sign in with device code",
          description: "Enter a code at github.com/login/device (fallback)",
          value: "device",
        },
      ],
      {
        placeHolder: "Choose sign-in method",
        title: "Refactor Agent: Sign in",
      }
    );

    if (!choice) {
      throw new vscode.CancellationError();
    }

    if (choice.value === "device") {
      return this._createSessionWithDeviceFlow();
    }

    return this._createSessionWithBrowser();
  }

  private _createSessionWithBrowser(): Promise<RefactorAgentSession> {
    const authUrl = this._getAuthSignInUrl();
    return new Promise<RefactorAgentSession>((resolve, reject) => {
      this._pendingResolve = resolve;
      this._pendingReject = reject;
      vscode.env.openExternal(vscode.Uri.parse(authUrl));
    });
  }

  private async _createSessionWithDeviceFlow(): Promise<RefactorAgentSession> {
    const clientId = await this._getClientId();
    if (!clientId) {
      throw new Error(
        "GitHub App client ID not configured. Set authSignInUrl or accessRequestUrl."
      );
    }

    const deviceCode = await this._requestDeviceCode(clientId);
    if (!deviceCode) {
      throw new Error("Failed to get device code from GitHub");
    }

    const message = `Enter code **${deviceCode.user_code}** at ${GITHUB_DEVICE_URI}`;
    const openBtn = "Open GitHub";
    const picked = await vscode.window.showInformationMessage(
      message,
      { modal: true },
      openBtn
    );
    if (picked === openBtn) {
      void vscode.env.openExternal(vscode.Uri.parse(GITHUB_DEVICE_URI));
    }

    const token = await this._pollForToken(
      clientId,
      deviceCode.device_code,
      deviceCode.interval
    );
    if (!token) {
      throw new Error("Device code expired or authorization was cancelled");
    }

    await this._registerDeviceToken(token);

    const session: RefactorAgentSession = {
      id: RefactorAgentAuthProvider.id,
      accessToken: token,
      account: { id: RefactorAgentAuthProvider.id, label: "Refactor Agent" },
      scopes: [],
    };
    void this._context.secrets.store(SESSION_SECRET_KEY, token);
    this._onDidChangeSessions.fire({
      added: [session],
      removed: [],
      changed: [],
    });
    return session;
  }

  private async _getClientId(): Promise<string> {
    const authSignInUrl = this._getAuthSignInUrl();
    try {
      const configUrl = authSignInUrl.replace(
        /\/auth\/signin\/?$/,
        "/auth/config.json"
      );
      const res = await fetch(configUrl);
      if (!res.ok) return "";
      const data = (await res.json()) as { clientId?: string };
      return data.clientId?.trim() ?? "";
    } catch {
      return "";
    }
  }

  private async _requestDeviceCode(
    clientId: string
  ): Promise<DeviceCodeResponse | null> {
    try {
      const body = new URLSearchParams({ client_id: clientId });
      const res = await fetch(GITHUB_DEVICE_CODE_URL, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: body.toString(),
      });
      if (!res.ok) return null;
      return (await res.json()) as DeviceCodeResponse;
    } catch {
      return null;
    }
  }

  private async _pollForToken(
    clientId: string,
    deviceCode: string,
    intervalSeconds: number
  ): Promise<string | null> {
    const body = new URLSearchParams({
      client_id: clientId,
      device_code: deviceCode,
      grant_type: "urn:ietf:params:oauth:grant-type:device_code",
    });
    const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

    for (let i = 0; i < 180; i++) {
      await wait(intervalSeconds * 1000);

      try {
        const res = await fetch(GITHUB_ACCESS_TOKEN_URL, {
          method: "POST",
          headers: { Accept: "application/json" },
          body: body.toString(),
        });
        const data = (await res.json()) as TokenResponse;
        if (data.access_token) return data.access_token;
        const err = data.error;
        if (err === "expired_token" || err === "access_denied") return null;
        if (err === "slow_down") intervalSeconds += 5;
      } catch {
        // continue polling
      }
    }
    return null;
  }

  private async _registerDeviceToken(token: string): Promise<void> {
    const registerUrl = this._getAuthRegisterDeviceUrl();
    const res = await fetch(registerUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      throw new Error(`Failed to register: ${res.status}`);
    }
  }

  private _getAuthRegisterDeviceUrl(): string {
    const config = vscode.workspace.getConfiguration("refactorAgent");
    const url = config.get<string>("authRegisterDeviceUrl", "");
    if (url && url.trim()) return url.trim();
    return "https://europe-west1-refactor-agent.cloudfunctions.net/auth-register-device";
  }

  async removeSession(_sessionId: string): Promise<void> {
    await this._context.secrets.delete(SESSION_SECRET_KEY);
    this._onDidChangeSessions.fire({
      added: [],
      removed: [],
      changed: [],
    });
  }

  /** Called by UriHandler when vscode://.../callback?token=... is opened. */
  handleCallback(uri: vscode.Uri): void {
    const params = new URLSearchParams(uri.query);
    const token = params.get("token");
    if (!token || !this._pendingResolve) {
      if (this._pendingReject) {
        this._pendingReject(new Error("No token received"));
        this._pendingReject = undefined;
        this._pendingResolve = undefined;
      }
      return;
    }
    const session: RefactorAgentSession = {
      id: RefactorAgentAuthProvider.id,
      accessToken: token,
      account: { id: RefactorAgentAuthProvider.id, label: "Refactor Agent" },
      scopes: [],
    };
    void this._context.secrets.store(SESSION_SECRET_KEY, token);
    this._pendingResolve(session);
    this._pendingResolve = undefined;
    this._pendingReject = undefined;
    this._onDidChangeSessions.fire({
      added: [session],
      removed: [],
      changed: [],
    });
  }

  private _getAuthSignInUrl(): string {
    const config = vscode.workspace.getConfiguration("refactorAgent");
    const authSignInUrl = config.get<string>("authSignInUrl", "");
    if (authSignInUrl && authSignInUrl.trim()) {
      return authSignInUrl.trim();
    }
    const accessRequestUrl = config.get<string>("accessRequestUrl", "");
    if (accessRequestUrl && accessRequestUrl.trim()) {
      try {
        const base = new URL(accessRequestUrl);
        return `${base.origin}/auth/signin`;
      } catch {
        // fall through
      }
    }
    return DEFAULT_AUTH_SIGNIN_URL;
  }
}
