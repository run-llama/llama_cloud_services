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
