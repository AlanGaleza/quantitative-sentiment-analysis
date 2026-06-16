export interface LoginRequest {
  email: string;
  password: string;
}

export interface CurrentUser {
  id: string;
  email: string;
}

export interface CurrentWorkspace {
  id: string;
  slug: string;
  name: string;
}

export interface AuthSessionResponse {
  user: CurrentUser;
  workspaces: CurrentWorkspace[];
  default_workspace_slug: string | null;
}

export interface AuthErrorBody {
  detail?: unknown;
}
