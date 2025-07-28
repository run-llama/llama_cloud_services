export type ClientParams = {
  apiKey?: string | undefined;
  baseUrl?: string | undefined;
};

export type CloudConstructorParams = {
  name: string;
  projectName: string;
  organizationId?: string | undefined;
} & ClientParams;
