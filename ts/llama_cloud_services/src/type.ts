export type ClientParams = {
  apiKey?: string | undefined;
  baseUrl?: string | undefined;
};

export type CloudConstructorParams = {
  name: string;
  projectName: string;
  organizationId?: string | undefined;
} & ClientParams;

export type ExtractResult = {
  data:
    | {
        [key: string]:
          | {
              [key: string]: unknown;
            }
          | Array<unknown>
          | string
          | number
          | number
          | boolean
          | null;
      }
    | Array<{
        [key: string]:
          | {
              [key: string]: unknown;
            }
          | Array<unknown>
          | string
          | number
          | number
          | boolean
          | null;
      }>
    | null;
  extractionMetadata: {
    [key: string]:
      | {
          [key: string]: unknown;
        }
      | Array<unknown>
      | string
      | number
      | number
      | boolean
      | null;
  };
};

export type ParseResult = {
  // eslint-disable-next-line  @typescript-eslint/no-explicit-any
  pages: Record<string, any>[];
  // eslint-disable-next-line  @typescript-eslint/no-explicit-any
  job_metadata: Record<string, any>;
  job_id: string;
  is_completed: boolean;
  file_path: string;
};
