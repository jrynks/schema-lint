export type IssueLevel = "error" | "warning";

export type UrlStatus = "OK" | "ERRORS" | "FETCH_FAILED";

export type Issue = {
  level: IssueLevel;
  type: string;
  path: string;
  message: string;
};

export type UrlResult = {
  url: string;
  status: UrlStatus;
  types_found: string[];
  issues: Issue[];
  jsonld_count: number;
};

export type SchemaLintReport = {
  schema: "schema-lint/v1";
  generated_at: string;
  results: UrlResult[];
  error_count: number;
  warning_count: number;
};

export type LdBlock = {
  raw: string;
  index: number;
  parsed: unknown;
  error: string | null;
};

export type Entity = {
  node: Record<string, unknown>;
  types: string[];
  blockIndex: number;
  path: string;
  context: unknown;
};

export type Extraction = {
  blocks: LdBlock[];
  entities: Entity[];
  typesFound: string[];
};

export type CheckOptions = {
  types?: string[] | null;
  strictTypes?: boolean;
  failOnFetch?: boolean;
};

export const SCHEMA_VERSION = "schema-lint/v1" as const;
export const DEFAULT_TYPES = ["Course", "LocalBusiness", "FAQPage"] as const;
export const OPTIONAL_TYPES = ["Organization", "WebSite", "BreadcrumbList"] as const;
