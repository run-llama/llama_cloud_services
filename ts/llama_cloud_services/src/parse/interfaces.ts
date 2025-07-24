export interface Pages {
  pages: Record<string, unknown>[];
}

export interface ParsingResult {
  markdown: undefined | string;
  json: undefined | Pages;
  text: undefined | string;
}
